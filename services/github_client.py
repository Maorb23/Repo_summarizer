# /services/github_client.py
# This module defines a GitHubClient class that provides methods for interacting with the GitHub API
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx

from ..settings import settings
from ..utils.errors import bad_request, not_found, upstream_error


GITHUB_REPO_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#?]+)"
)


class GitHubClient:
    def __init__(self) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "repo-summarizer/0.1",
        }
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        self._client = httpx.AsyncClient(
            base_url=settings.github_api_base,
            headers=headers,
            timeout=httpx.Timeout(settings.http_timeout_s),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @staticmethod
    def parse_repo_url(url: str) -> Tuple[str, str]:
        m = GITHUB_REPO_RE.match(url)
        if not m:
            raise bad_request("github_url must be a public GitHub repo URL like https://github.com/OWNER/REPO")
        owner = m.group("owner")
        repo = m.group("repo").rstrip(".git")
        return owner, repo

    async def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        r = await self._client.get(f"/repos/{owner}/{repo}")
        if r.status_code == 404:
            raise not_found("Repository not found (is it public and spelled correctly?)")
        if r.status_code >= 400:
            raise upstream_error(f"GitHub error: {r.status_code} {r.text}")
        return r.json()

    async def get_languages(self, owner: str, repo: str) -> Dict[str, int]:
        r = await self._client.get(f"/repos/{owner}/{repo}/languages")
        if r.status_code >= 400:
            return {}
        return r.json()

    async def get_branch_tree_sha(self, owner: str, repo: str, branch: str) -> str:
        r = await self._client.get(f"/repos/{owner}/{repo}/branches/{branch}")
        if r.status_code >= 400:
            raise upstream_error(f"GitHub branch lookup failed: {r.status_code} {r.text}")
        data = r.json()
        return data["commit"]["commit"]["tree"]["sha"]

    async def get_tree(self, owner: str, repo: str, tree_sha: str) -> Dict[str, Any]:
        # recursive tree
        r = await self._client.get(f"/repos/{owner}/{repo}/git/trees/{tree_sha}", params={"recursive": "1"})
        if r.status_code >= 400:
            raise upstream_error(f"GitHub tree fetch failed: {r.status_code} {r.text}")
        return r.json()

    async def get_readme(self, owner: str, repo: str, ref: str) -> Optional[Dict[str, Any]]:
        r = await self._client.get(f"/repos/{owner}/{repo}/readme", params={"ref": ref})
        if r.status_code >= 400:
            return None
        return r.json()

    async def get_file(self, owner: str, repo: str, path: str, ref: str) -> Optional[Dict[str, Any]]:
        r = await self._client.get(f"/repos/{owner}/{repo}/contents/{path}", params={"ref": ref})
        if r.status_code >= 400:
            return None
        return r.json()

    async def get_root_contents(self, owner: str, repo: str, ref: str) -> List[Dict[str, Any]]:
        r = await self._client.get(f"/repos/{owner}/{repo}/contents", params={"ref": ref})
        if r.status_code >= 400:
            return []
        data = r.json()
        return data if isinstance(data, list) else []