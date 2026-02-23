# /services/summarize_service.py
# This module defines the SummarizeService class, which orchestrates the process of summarizing 
# a GitHub repository.
from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from cachetools import TTLCache

from ..services.github_client import GitHubClient
from ..services.repo_processor import RepoContext, select_and_load_files
from ..services.llm_client import NebiusLLMClient
from ..services.summarizer import RepoSummarizer
from ..utils.errors import upstream_error


class SummarizeService:
    def __init__(self, github: GitHubClient, llm: NebiusLLMClient) -> None:
        self.github = github
        self.llm = llm
        self.summarizer = RepoSummarizer(llm)

        self.cache = TTLCache(maxsize=512, ttl=600)

    async def summarize_repo(self, github_url: str) -> Dict[str, Any]:
        if github_url in self.cache:
            return self.cache[github_url]

        owner, repo = self.github.parse_repo_url(github_url)
        repo_meta = await self.github.get_repo(owner, repo)
        default_branch = repo_meta.get("default_branch") or "main"

        languages = await self.github.get_languages(owner, repo)
        topics = repo_meta.get("topics") or []
        homepage = repo_meta.get("homepage")

        # Tree
        tree_sha = await self.github.get_branch_tree_sha(owner, repo, default_branch)
        tree = await self.github.get_tree(owner, repo, tree_sha)
        tree_items = tree.get("tree") or []
        if isinstance(tree.get("truncated"), bool) and tree["truncated"]:
            # fallback: can't rely on full recursive tree
            root = await self.github.get_root_contents(owner, repo, default_branch)
            tree_items = []
            for it in root:
                if it.get("type") == "file":
                    tree_items.append({"type": "blob", "path": it.get("path"), "size": it.get("size")})
                elif it.get("type") == "dir":
                    # we won't expand; structure hint will still show it
                    tree_items.append({"type": "tree", "path": it.get("path")})

        # safety cap
        if len(tree_items) > 6000:
            tree_items = tree_items[:6000]

        selected_files, structure_hint, extracted_tech = await select_and_load_files(
            github=self.github,
            owner=owner,
            repo=repo,
            ref=default_branch,
            tree_items=tree_items,
        )

        ctx = RepoContext(
            full_name=repo_meta.get("full_name", f"{owner}/{repo}"),
            description=repo_meta.get("description") or "",
            default_branch=default_branch,
            languages=languages,
            topics=topics,
            homepage=homepage,
            structure_hint=structure_hint,
            selected_files=selected_files,
            extracted_tech=extracted_tech,
        )

        if not self.llm.enabled:
            # Fallback to a non-LLM summary so /summarize still returns a response.
            # (You’ll likely want NEBIUS_API_KEY in real usage.)
            out = {
                "summary": (
                    f"**{ctx.full_name}** is a software repository. "
                    f"GitHub description: {ctx.description or 'N/A'}. "
                    f"This response was generated without an LLM because `NEBIUS_API_KEY` is not set."
                ),
                "technologies": list((list(languages.keys()) + extracted_tech)[:12]) or ["Unknown"],
                "structure": structure_hint,
            }
            self.cache[github_url] = out
            return out

        out = await self.summarizer.summarize(ctx)
        self.cache[github_url] = out
        return out