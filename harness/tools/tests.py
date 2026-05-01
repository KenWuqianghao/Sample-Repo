"""Pytest invocation."""

from __future__ import annotations

import shlex
import subprocess


def run_tests(target: str = "", verbose: bool = False) -> str:
    """Run pytest in /app workspace."""
    from harness.state import workspace_root

    root = str(workspace_root())
    cmd = ["pytest"]
    if not verbose:
        cmd.append("-q")
    cmd.append("--tb=short")
    if target:
        cmd.extend(shlex.split(target))
    else:
        cmd.append(".")
    try:
        proc = subprocess.run(
            cmd, cwd=root, capture_output=True, text=True, timeout=600, check=False
        )
        merged = ""
        if proc.stdout:
            merged += proc.stdout
        if proc.stderr:
            merged += ("\n" if merged else "") + proc.stderr
        if len(merged) > 14000:
            merged = merged[:14000] + "\n…truncated"
        return f"exit={proc.returncode}\n{merged or '(no output)'}"
    except subprocess.TimeoutExpired:
        return "pytest timed out"
