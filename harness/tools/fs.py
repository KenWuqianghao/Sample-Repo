"""Filesystem + ripgrep search under the workspace."""

from __future__ import annotations

import subprocess
from pathlib import Path


def workspace() -> Path:
    from harness.state import workspace_root

    return workspace_root()


def _safe_path(path: str) -> Path:
    root = workspace().resolve()
    resolved = (root / path).resolve()
    if not str(resolved).startswith(str(root) + "/") and resolved != root:
        raise ValueError(f"path escapes workspace: {path!r}")
    return resolved


def read_file(path: str, max_chars: int = 80_000) -> str:
    try:
        p = _safe_path(path)
    except ValueError as e:
        return f"read failed: {e}"
    try:
        data = p.read_text(encoding="utf-8")
    except OSError as e:
        return f"read failed: {e}"
    return data if len(data) <= max_chars else data[:max_chars] + "\n…truncated"


def write_file(path: str, content: str) -> str:
    try:
        p = _safe_path(path)
    except ValueError as e:
        return f"write failed: {e}"
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    except OSError as e:
        return f"write failed: {e}"
    return f"wrote {p}"


def search(pattern: str, subdir: str = ".", max_matches: int = 50) -> str:
    root = workspace() / subdir
    if not root.exists():
        return "search root missing"
    try:
        proc = subprocess.run(
            [
                "rg",
                "--line-number",
                "--max-count",
                str(max_matches),
                pattern,
                str(root),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        out = proc.stdout.strip() or proc.stderr.strip() or "(no matches)"
        if len(out) > 12000:
            return out[:12000] + "\n…truncated"
        return out
    except FileNotFoundError:
        return "rg not installed in sandbox image"
    except subprocess.TimeoutExpired:
        return "search timed out"
