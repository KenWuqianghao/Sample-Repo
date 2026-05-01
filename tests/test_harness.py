"""Tests for in-sandbox coding harness."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from harness.engine import run_turn
from harness.run import main


def test_run_turn_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    out = run_turn("hello")
    assert "ANTHROPIC_API_KEY" in out or "placeholder" in out.lower()


def _mock_response(text: str, stop_reason: str = "end_turn") -> MagicMock:
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    response = MagicMock()
    response.stop_reason = stop_reason
    response.content = [text_block]
    return response


def test_run_turn_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("HARNESS_MODEL", "claude-opus-4-7")

    with patch("harness.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_response("  done  ")

        assert run_turn("ping") == "done"


def test_run_turn_tool_then_end(monkeypatch: pytest.MonkeyPatch) -> None:
    """One tool call followed by a final text response."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("HARNESS_MODEL", "claude-opus-4-7")
    monkeypatch.setenv("HARNESS_AUTONOMY", "none")

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = "toolu_01"
    tool_block.name = "git_status"
    tool_block.input = {}

    tool_response = MagicMock()
    tool_response.stop_reason = "tool_use"
    tool_response.content = [tool_block]

    with patch("harness.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [
            tool_response,
            _mock_response("all good"),
        ]

        with patch("harness.tools.registry.git_ops.git_status_summary", return_value="clean"):
            result = run_turn("what's the status?")

    assert result == "all good"
    assert mock_client.messages.create.call_count == 2


def test_cli_json_output(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["harness.run", "--prompt", "hi", "--output-format", "json"],
    )
    main()
    captured = capsys.readouterr().out.strip()
    data = json.loads(captured)
    assert "result" in data
