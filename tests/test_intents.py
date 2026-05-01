"""Intent parsing for one-word UX."""

from __future__ import annotations

import pytest
from harness.intents import Intent, extract_last_user_utterance, handle_intent, parse_intent
from harness.state import state_file_path


def test_parse_intent_aliases() -> None:

    assert parse_intent("status") == Intent.STATUS

    assert parse_intent("cancel") == Intent.STOP

    assert parse_intent("ok") == Intent.GO


def test_extract_last_user_block() -> None:

    blob = "[USER]: first\n[AGENT]: mid\n[USER]: last prompt"

    assert extract_last_user_utterance(blob) == "last prompt"


def test_handle_intent_status_default_state(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:

    monkeypatch.setenv("HARNESS_WORKDIR", str(tmp_path))

    reply = handle_intent(Intent.STATUS, state_path=state_file_path())

    assert "branch=?;" in reply

    assert "idle" in reply
