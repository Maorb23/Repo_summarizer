# /services/repo_processor.py
# This module contains the core logic for processing a GitHub repository, including selecting 
# informative files, fetching their content, and extracting relevant information to build the context 
# for summarization.
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Tuple
import json

from settings import settings
from utils.text import BINARY_EXTS, is_probably_binary_bytes, safe_b64decode, truncate

# We use async coding for all Github client interactions to allow for concurrent requests to prevent bottlenecks. 


IGNORE_DIRS = {
    ".git", ".github", ".idea", ".vscode",
    "node_modules", "dist", "build", "out",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "env",
    "vendor",
    ".next", ".nuxt",
}

IGNORE_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "pdm.lock", "pipfile.lock",
    ".DS_Store",
}

IMPORTANT_BASENAMES = [
    "README.md", "README.rst", "README.txt", "README",
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "Pipfile", "environment.yml",
    "Dockerfile", "docker-compose.yml", "compose.yml",
    "mkdocs.yml", "docs/conf.py",
    "manage.py", "wsgi.py", "asgi.py", "app.py", "main.py"
    "package.json", "tsconfig.json",
    "go.mod", "Cargo.toml",
]


TEXT_EXT_ALLOW = {
    ".py", ".md", ".rst", ".txt",
    ".toml", ".cfg", ".ini", ".yml", ".yaml", ".json",
    ".js", ".ts", ".tsx", ".jsx",
    ".go", ".rs", ".java", ".kt", ".cs", ".cpp", ".c", ".h",
    ".sh", ".bat",
    ".html", ".css",
}


@dataclass
class SelectedFile:
    path: str
    reason: str
    content: str  # truncated text


@dataclass
class RepoContext:
    full_name: str
    description: str
    default_branch: str
    languages: Dict[str, int]
    topics: List[str]
    homepage: str | None
    structure_hint: str
    selected_files: List[SelectedFile]
    extracted_tech: List[str]


def _ext(path: str) -> str:
    return PurePosixPath(path).suffix.lower()


def _basename(path: str) -> str:
    return PurePosixPath(path).name


def _ignored(path: str) -> bool:
    p = PurePosixPath(path)
    if _basename(path) in IGNORE_FILES:
        return True
    for part in p.parts:
        if part in IGNORE_DIRS:
            return True
    if _ext(path) in BINARY_EXTS:
        return True
    return False


def _is_text_candidate(path: str) -> bool:
    ext = _ext(path)
    if ext in TEXT_EXT_ALLOW:
        return True
    # allow extensionless important files like Dockerfile, LICENSE
    base = _basename(path)
    if base in {"Dockerfile", "LICENSE", "Makefile"}:
        return True
    return False


def score_path(path: str, size: int | None) -> Tuple[int, str]:
    base = _basename(path)
    p = PurePosixPath(path)

    if base.upper().startswith("README"):
        return 10_000, "README"
    if base in IMPORTANT_BASENAMES:
        return 7_000, "Key project/config file"
    if "docs" in p.parts:
        return 2_000, "Documentation"
    if any(part in {"src", "app", "apps"} for part in p.parts):
        return 1_600, "Main source directory"
    if any(part in {"tests", "test"} for part in p.parts):
        return 900, "Tests"

    sc = 300
    reason = "Source/text file"
    if size is not None:
        # prefer smaller files; huge files are less useful for summary
        sc += max(0, 600 - min(size, 60_000) // 100)
    return sc, reason


def build_structure_hint(tree_paths: List[str]) -> str:
    # concise "layout" based on top-level dirs
    top = {}
    for path in tree_paths:
        p = PurePosixPath(path)
        if len(p.parts) == 0:
            continue
        k = p.parts[0]
        top[k] = top.get(k, 0) + 1

    # show up to 8 most frequent top-level dirs/files
    items = sorted(top.items(), key=lambda x: x[1], reverse=True)[:8]
    parts = [f"`{name}/` ({count} items)" if name and "." not in name else f"`{name}` ({count})" for name, count in items]
    return "Top-level layout: " + ", ".join(parts) if parts else "Top-level layout: (could not infer)"


def extract_tech_from_files(file_texts: Dict[str, str]) -> List[str]:
    tech = set()

    # requirements.txt
    req = file_texts.get("requirements.txt")
    if req:
        for line in req.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pkg = line.split("==")[0].split(">=")[0].split("<=")[0].split("[")[0].strip()
            if pkg:
                tech.add(pkg)

    # package.json
    pj = file_texts.get("package.json")
    if pj:
        try:
            data = json.loads(pj)
            for section in ("dependencies", "devDependencies"):
                deps = data.get(section, {}) or {}
                for k in deps.keys():
                    tech.add(k)
        except Exception:
            pass

    # pyproject.toml (best-effort; no full TOML parse to keep deps minimal)
    pyproj = file_texts.get("pyproject.toml")
    if pyproj:
        lowered = pyproj.lower()
        if "django" in lowered:
            tech.add("Django")
        if "fastapi" in lowered:
            tech.add("FastAPI")
        if "torch" in lowered:
            tech.add("PyTorch")

    return sorted(tech)[:25]


async def select_and_load_files(
    github,  # GitHubClient
    owner: str,
    repo: str,
    ref: str,
    tree_items: List[Dict[str, Any]],
) -> Tuple[List[SelectedFile], str, List[str]]:
    """
    Pick top N informative text files and fetch their content (truncated).
    """
    # 1) candidates
    candidates: List[Tuple[int, str, str, int | None]] = []
    all_paths: List[str] = []

    for item in tree_items:
        if item.get("type") != "blob":
            continue
        path = item.get("path")
        if not path:
            continue
        all_paths.append(path)

        if _ignored(path) or not _is_text_candidate(path):
            continue

        size = item.get("size") if isinstance(item.get("size"), int) else None
        if size is not None and size > settings.max_file_bytes:
            continue

        score, reason = score_path(path, size)
        candidates.append((score, path, reason, size))

    # cap huge repos
    candidates.sort(key=lambda x: x[0], reverse=True)
    candidates = candidates[: settings.max_files * 4]  # extra buffer before fetching

    structure_hint = build_structure_hint(all_paths)

    selected: List[SelectedFile] = []
    loaded_texts: Dict[str, str] = {}

    # 2) always try README first via /readme
    readme_obj = await github.get_readme(owner, repo, ref)
    if readme_obj and readme_obj.get("content"):
        b = safe_b64decode(readme_obj["content"])
        if not is_probably_binary_bytes(b):
            txt = b.decode("utf-8", errors="replace")
            txt = truncate(txt, settings.max_readme_chars)
            selected.append(SelectedFile(path=readme_obj.get("path", "README"), reason="README", content=txt))

    # 3) fetch other top candidates until context budget
    total_chars = sum(len(x.content) for x in selected)
    for score, path, reason, _size in candidates:
        if len(selected) >= settings.max_files:
            break
        # avoid re-adding README if already got it
        if PurePosixPath(path).name.upper().startswith("README") and any(s.reason == "README" for s in selected):
            continue

        # stay within overall context budget
        if total_chars >= settings.max_total_context_chars:
            break

        obj = await github.get_file(owner, repo, path, ref)
        if not obj or obj.get("type") != "file" or not obj.get("content"):
            continue

        b = safe_b64decode(obj["content"])
        if is_probably_binary_bytes(b):
            continue

        txt = b.decode("utf-8", errors="replace")
        # per-file truncate based on remaining budget
        remaining = max(2_000, settings.max_total_context_chars - total_chars)
        txt = truncate(txt, min(12_000, remaining))
        selected.append(SelectedFile(path=path, reason=reason, content=txt))
        total_chars += len(txt)

        # keep a map by basename for tech extraction
        loaded_texts[_basename(path)] = txt

    extracted_tech = extract_tech_from_files(loaded_texts)
    return selected, structure_hint, extracted_tech