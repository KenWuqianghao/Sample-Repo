"""GitHub REST (draft PR + gist) using ``GITHUB_TOKEN``."""

from __future__ import annotations

import os
from typing import Any

import httpx

GH_API = "https://api.github.com"


def _token() -> str:
    token = (
        os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_ACCESS_TOKEN")
        or ""
    ).strip()

    if not token:
        raise RuntimeError("GITHUB_TOKEN missing for GitHub API calls")

    return token


def parse_repo_slug() -> tuple[str, str]:
    slug = os.environ.get("REPO_URL", "").strip()
    parts = slug.split("/")
    if len(parts) == 2 and all(parts):
        return parts[0], parts[1]
    raise RuntimeError("REPO_URL must be owner/repo (no https prefix)")


def default_branch(owner: str, repo: str) -> str:
    headers = {"Authorization": f"bearer {_token()}", "Accept": "application/vnd.github+json"}

    resp = httpx.get(f"{GH_API}/repos/{owner}/{repo}", headers=headers, timeout=60.0)
    resp.raise_for_status()
    return str(resp.json().get("default_branch") or "main")


def create_draft_pr(head: str, title: str, body: str) -> str:
    owner, repo = parse_repo_slug()
    base_branch = os.environ.get("HARNESS_REPO_BASE_BRANCH") or default_branch(owner, repo)
    tok = _token()

    resp = httpx.post(
        f"{GH_API}/repos/{owner}/{repo}/pulls",
        headers={
            "Authorization": f"bearer {tok}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "title": title,
            "body": body,
            "head": head,
            "base": base_branch,
            "draft": True,
        },
        timeout=120.0,
    )
    if resp.status_code >= 400:
        return f"draft PR HTTP {resp.status_code}: {resp.text[:600]}"
    data: dict[str, Any] = resp.json()
    return str(data.get("html_url") or data)


def create_gist(description: str, filename: str, content: str, public: bool = False) -> str:
    """Return gist HTML URL."""

    tok = _token()
    fname = filename.strip() or "scratch.txt"

    resp = httpx.post(
        f"{GH_API}/gists",
        headers={"Authorization": f"bearer {tok}", "Accept": "application/vnd.github+json"},
        json={
            "description": description,
            "public": public,
            "files": {fname: {"content": content or ""}},
        },
        timeout=120.0,
    )
    if resp.status_code >= 400:
        return f"gist HTTP {resp.status_code}: {resp.text[:600]}"
    data: dict[str, Any] = resp.json()
    return str(data.get("html_url") or data)
