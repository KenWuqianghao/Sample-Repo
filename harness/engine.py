"""
Coding harness backend: customize `harness/agent.py` for the tool loop.

``run_turn`` is the stable entry used by tests and thin CLIs; it suppresses
stdout emissions (no progress / final JSON lines).
"""

from __future__ import annotations

from harness.agent import run as agent_run


def run_turn(prompt: str) -> str:
    """Execute one user turn; return plain-text reply for iMessage / JSON wrapper."""
    return agent_run(
        prompt,
        emit_progress=False,
        emit_final_json_line=False,
    )
