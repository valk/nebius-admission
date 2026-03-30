import httpx
import asyncio
from typing import List, Dict, Any, Optional
import os
import base64
from models.summarize import RepoMetadata

class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Repo-Summarizer"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
        self.client = httpx.AsyncClient(headers=self.headers, follow_redirects=True)

    async def close(self):
        await self.client.aclose()

    def _parse_url(self, url: str) -> tuple[str, str]:
        # Simple parser for https://github.com/owner/repo
        parts = url.rstrip("/").split("/")
        if len(parts) < 5 or parts[2] != "github.com":
            raise ValueError("Invalid GitHub URL. Expected format: https://github.com/owner/repo")
        return parts[3], parts[4]

    async def get_repo_metadata(self, url: str) -> RepoMetadata:
        owner, repo = self._parse_url(url)
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        
        resp = await self.client.get(api_url)
        if resp.status_code == 404:
            raise ValueError(f"Repository {owner}/{repo} not found or is private.")
        resp.raise_for_status()
        data = resp.json()

        return RepoMetadata(
            name=data["name"],
            owner=data["owner"]["login"],
            description=data.get("description"),
            primary_language=data.get("language"),
            stars=data.get("stargazers_count", 0)
        )

    async def get_file_content(self, owner: str, repo: str, path: str) -> str:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        resp = await self.client.get(url)
        resp.raise_for_status()
        data = resp.json()
        if "content" in data:
            return base64.b64decode(data["content"]).decode("utf-8")
        return ""

    async def get_raw_file_url(self, owner: str, repo: str, path: str, branch: str = "main") -> str:
        # Fallback for large files or simple fetches
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"

    async def fetch_file_text(self, url: str) -> str:
        resp = await self.client.get(url)
        if resp.status_code == 200:
            return resp.text
        return ""

    async def get_repo_tree(self, owner: str, repo: str, recursive: bool = True) -> List[Dict[str, Any]]:
        # Get the default branch first
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        resp = await self.client.get(api_url)
        resp.raise_for_status()
        default_branch = resp.json().get("default_branch", "idk") # Should handle correctly
        
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}"
        if recursive:
            tree_url += "?recursive=1"
            
        resp = await self.client.get(tree_url)
        if resp.status_code != 200:
             # Fallback if tree is too large or other issues
             return []
        return resp.json().get("tree", [])
