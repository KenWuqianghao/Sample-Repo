"""Harness shell policy helpers."""

from __future__ import annotations

from harness.policy import allow_tool_call, is_shell_denied


def test_denies_recursive_root_rm() -> None:

    deny, _ = is_shell_denied("rm -rf /")

    assert deny is True

    deny2, _ = is_shell_denied("rm -rf /tmp/foo")

    assert deny2 is False


def test_allows_ls() -> None:

    deny, _ = is_shell_denied("ls -la")

    assert deny is False


def test_allow_run_shell_blocks_pipe_shell() -> None:

    ok, _ = allow_tool_call("run_shell", '{"command": "echo hi | bash"}')

    assert not ok


def test_allow_git_push_rejects_force() -> None:

    ok, _ = allow_tool_call("git_push", '{"branch": "x", "force": true}')
    assert not ok

    ok2, _ = allow_tool_call("git_push", '{"branch": "x", "force": false}')

    assert ok2
