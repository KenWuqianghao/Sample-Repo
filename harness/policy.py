"""Guardrails for tool execution (sandbox + mobile UX)."""

from __future__ import annotations

import re


def is_shell_denied(command: str) -> tuple[bool, str]:
    c = command.strip()
    low = c.lower()

    if not c:
        return True, "empty command"

    # Root rm -rf (but allow rm -rf /app, /tmp, etc.)
    if re.search(r"rm\s+-rf\s+/(?:\s|$)", low) or "rm -rf /*" in low:
        return True, "recursive delete at filesystem root denied"

    needles = (
        "mkfs.",
        "> /dev/sd",
        "dd if=/dev/zero",
        "git push --force",
        "git push -f",
        ":(){",
        "> ~/.ssh/",
    )
    for n in needles:
        if n in low:
            return True, f"blocked shell ({n})"

    if "| sh" in low or "| bash" in low:
        return True, "pipe-to-shell denied"

    if "chmod 777 /" in low or "chmod -r /" in low:
        return True, "destructive chmod"

    return False, ""


def allow_tool_call(name: str, arguments_json: str) -> tuple[bool, str]:
    """Return (ok, denial_reason)."""
    import json

    if name == "run_shell":
        try:
            args = json.loads(arguments_json)
        except json.JSONDecodeError:
            return False, "invalid tool JSON"
        cmd = str(args.get("command", ""))

        bad, why = is_shell_denied(cmd)
        if bad:
            return False, why

    if name == "git_push":
        try:
            args = json.loads(arguments_json)
        except json.JSONDecodeError:
            return False, "invalid tool JSON"
        if args.get("force"):
            return False, "forced push denied"

    return True, ""
