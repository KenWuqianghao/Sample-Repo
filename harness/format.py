"""Mobile-friendly formatting and deliverable routing heuristics."""

from __future__ import annotations

import os
from typing import Any, Literal

DeliverableKind = Literal["inline", "pr", "gist"]


def split_for_imessage(text: str, max_len: int | None = None) -> list[str]:
    """Split long text into multiple bubbles with ``(i/n)`` markers."""

    cap = max_len or int(os.environ.get("HARNESS_MAX_REPLY_CHARS", "800"))
    cap = max(200, cap)
    t = text.strip()
    if len(t) <= cap:
        return [t]

    chunks: list[str] = []
    for i in range(0, len(t), cap):
        chunks.append(t[i : i + cap].rstrip())
    total = len(chunks)
    return [f"{c} ({idx + 1}/{total})" for idx, c in enumerate(chunks)]


def pick_deliverable(
    *,
    changed_files: int,
    insertion_plus_deletion: int,
    response_text_len: int,
    has_repo: bool,
) -> DeliverableKind:
    """Cheap heuristic: PR when real multi-file edits, gist for long text-only, else inline."""

    if not has_repo:
        return "gist" if response_text_len > 4000 else "inline"
    if changed_files >= 2 or insertion_plus_deletion >= 80:
        return "pr"
    if changed_files == 1 and insertion_plus_deletion >= 40:
        return "pr"
    if response_text_len > 9000:
        return "gist"
    return "inline"


def summarize_tool_payload(payload: dict[str, Any]) -> str:
    if payload.get("type") != "progress":
        return ""
    return str(payload.get("tool", "?"))
