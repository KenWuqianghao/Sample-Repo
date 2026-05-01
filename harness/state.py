"""Session state persisted under the repo workspace (``/app`` in sandboxes)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_WORKSPACE = "/app"
STATE_DIR = ".harness"
STATE_FILENAME = "state.json"


def workspace_root() -> Path:
    return Path(os.environ.get("HARNESS_WORKDIR", DEFAULT_WORKSPACE)).resolve()


def state_file_path() -> Path:
    return workspace_root() / STATE_DIR / STATE_FILENAME


def load_state(path: Path | None = None) -> dict[str, Any]:
    p = path or state_file_path()
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def save_state(updates: dict[str, Any], path: Path | None = None) -> None:
    p = path or state_file_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    current = load_state(p)
    current.update(updates)
    p.write_text(json.dumps(current, indent=2), encoding="utf-8")


def update_step(label: str, path: Path | None = None) -> None:
    save_state({"last_step": label, "last_step_at": _iso_now()}, path)


def _iso_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
