"""Sandbox image definition and factory."""

from __future__ import annotations

import logging

import modal

log = logging.getLogger(__name__)

GITHUB_SECRET = modal.Secret.from_name("github-token")
SANDBOX_SECRETS = [
    modal.Secret.from_name("model-secrets"),
    GITHUB_SECRET,
]

REPO_IMAGE = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git", "curl", "build-essential", "ripgrep")
    .pip_install(
        "pytest",
        "pytest-asyncio",
        "ruff",
        "httpx",
        "fastapi",
        "uvicorn",
    )
    .run_commands(
        # v2: force cache bust after initial push of harness code
        "true",
        (
            "bash -lc 'git clone "
            '"https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO_URL}.git" /app\''
        ),
        (
            'bash -lc \'cd /app && (pip install -e ".[dev]" || pip install -e . || '
            "pip install .) || true'"
        ),
        secrets=[GITHUB_SECRET],
    )
    .env({"PYTHONPATH": "/app", "HOME": "/root"})
)

SNAPSHOT_META = modal.Dict.from_name("snapshot-meta", create_if_missing=True)


def _resolve_sandbox_image() -> modal.Image:
    """Prefer a filesystem snapshot image if cron has published one."""
    try:
        snap_id = SNAPSHOT_META.get("image_id")
    except Exception:
        snap_id = None
    if not snap_id:
        return REPO_IMAGE
    try:
        return modal.Image.from_id(str(snap_id))
    except Exception:
        log.warning("snapshot_image_unavailable image_id=%s", snap_id)
        return REPO_IMAGE


def spawn_sandbox(app: modal.App, ttl_seconds: int = 3600) -> modal.Sandbox:
    """Create a long-running sandbox for the coding harness."""
    image = _resolve_sandbox_image()
    return modal.Sandbox.create(
        "sleep",
        "infinity",
        image=image,
        app=app,
        cpu=2.0,
        memory=4096,
        timeout=ttl_seconds,
        secrets=SANDBOX_SECRETS,
    )


__all__ = ["REPO_IMAGE", "SNAPSHOT_META", "SANDBOX_SECRETS", "spawn_sandbox"]
