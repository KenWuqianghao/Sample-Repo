"""Tests for session helpers (no Modal runtime)."""

from __future__ import annotations

from modal_app.agent import build_full_prompt, parse_agent_output
from modal_app.session import (
    HISTORY_MAX_ENTRIES,
    should_respawn_sandbox,
    trim_session_history,
    validate_e164,
)


def test_trim_session_history_caps_at_max() -> None:
    hist = [{"role": "user", "content": str(i), "msg_id": f"m{i}"} for i in range(50)]
    out = trim_session_history(hist)
    assert len(out) == HISTORY_MAX_ENTRIES
    assert out[0]["content"] == str(50 - HISTORY_MAX_ENTRIES)


def test_should_respawn_when_poll_returns_code() -> None:
    assert should_respawn_sandbox(None) is False
    assert should_respawn_sandbox(0) is True
    assert should_respawn_sandbox(1) is True


def test_validate_e164() -> None:
    assert validate_e164("+16505550100") is True
    assert validate_e164("16505550100") is False
    assert validate_e164("+06505550100") is False
    assert validate_e164("+1") is False


def test_build_full_prompt_includes_tail() -> None:
    history: list[dict] = [
        {"role": "user", "content": "a", "msg_id": "1"},
        {"role": "agent", "content": "b", "msg_id": "2"},
    ]
    p = build_full_prompt("c", history)
    assert "[USER]: a" in p
    assert "[AGENT]: b" in p
    assert "[USER]: c" in p


def test_parse_agent_output_prefers_json_field() -> None:
    text = parse_agent_output(['{"result": "done"}'])
    assert text == "done"


def test_parse_agent_output_prefers_final_payload() -> None:
    assert (
        parse_agent_output(
            ['{"type": "progress"}', '{"type": "final", "result": "all set"}'],
        )
        == "all set"
    )


def test_parse_agent_output_joins_plain_lines() -> None:
    assert parse_agent_output(["line1", "line2"]) == "line1\nline2"
