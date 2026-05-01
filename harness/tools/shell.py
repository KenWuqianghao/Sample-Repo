"""Bounded shell runner."""

from __future__ import annotations

import subprocess


def run_shell(command: str, cwd: str | None = None, timeout_s: int = 120) -> str:
    from harness.state import workspace_root

    cwd_path = cwd or str(workspace_root())
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=cwd_path,
            capture_output=True,
            text=True,
            timeout=min(timeout_s, 600),
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        lines = ""
        if stdout:
            lines += stdout
        if stderr:
            lines += ("\n" if lines else "") + stderr
        if not lines:
            lines = "(no output)"
        header = f"exit={proc.returncode}\n"
        text = header + lines
        if len(text) > 15000:
            return text[:15000] + "\n…truncated"
        return text
    except subprocess.TimeoutExpired:
        return "exit=? (timed out)"
