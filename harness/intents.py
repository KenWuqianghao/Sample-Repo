"""One-word control intents for SMS/iMessage UX."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path


class Intent(StrEnum):
    STOP = "stop"
    STATUS = "status"
    UNDO = "undo"
    PR = "pr"
    DIFF = "diff"
    TESTS = "tests"
    GO = "go"


def extract_last_user_utterance(full_prompt: str) -> str:
    """Parse the last ``[USER]:`` line from ``build_full_prompt`` output."""

    last = ""
    for line in full_prompt.splitlines():
        if line.startswith("[USER]: "):
            last = line.removeprefix("[USER]: ").strip()
    return last or full_prompt.strip()


def parse_intent(text: str) -> Intent | None:
    t = text.strip().lower()
    if not t:
        return None
    first = t.split()[0] if t.split() else t
    mapping: dict[str, Intent] = {
        "stop": Intent.STOP,
        "abort": Intent.STOP,
        "cancel": Intent.STOP,
        "status": Intent.STATUS,
        "undo": Intent.UNDO,
        "pr": Intent.PR,
        "pull": Intent.PR,
        "diff": Intent.DIFF,
        "patch": Intent.DIFF,
        "tests": Intent.TESTS,
        "test": Intent.TESTS,
        "pytest": Intent.TESTS,
        "go": Intent.GO,
        "yes": Intent.GO,
        "ok": Intent.GO,
    }
    return mapping.get(t) or mapping.get(first)


def handle_intent(
    intent: Intent,
    *,
    state_path: Path,
) -> str | None:
    """Return an iMessage-ready reply for an intent."""

    from harness.state import load_state

    state = load_state(state_path)

    if intent == Intent.STATUS:
        return (
            "Status: "
            f"branch={state.get('branch', '?')}; "
            f"last_step={state.get('last_step', 'idle')}; "
            f"last_pr={state.get('last_pr_url', 'none')}"
        )

    if intent == Intent.PR:
        url = state.get("last_pr_url")
        return f"Last PR: {url}" if url else "No PR recorded yet for this session."

    if intent == Intent.DIFF:
        return (
            "Open the PR or gist link from the last reply for the full diff; "
            "iMessage is not a good surface for patches."
        )

    if intent == Intent.TESTS:
        return (
            "Reply with the path or area to test (e.g. tests/test_foo.py); "
            "I'll run pytest on the next task."
        )

    if intent in (Intent.STOP, Intent.UNDO, Intent.GO):
        return (
            f"Noted ({intent.value}). Send your next coding request when ready; "
            "branch/PR work continues on the next full run."
        )

    return None


def format_state_brief(path: Path) -> str:
    if not path.exists():
        return "(no state file yet)"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))

    except (OSError, json.JSONDecodeError):
        return "(state unreadable)"
    return json.dumps(data, indent=0)[:1200]
