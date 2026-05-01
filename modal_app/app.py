"""Deployable Modal app: ASGI webhook, session worker, agent, and cron snapshot."""

from __future__ import annotations

import modal

from modal_app import agent, session, snapshot
from modal_app.state import modal_app

app = modal_app

__all__ = [
    "app",
    "modal_app",
    "fastapi_app",
    "session_manager",
    "run_agent",
    "refresh_snapshot",
]


@modal_app.function(
    min_containers=1,
    buffer_containers=1,
    scaledown_window=3600,
    startup_timeout=600,
    timeout=600,
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app(label="imessage-coding-agent")
def fastapi_app():
    from webhook.server import create_app

    return create_app(load_env=False)


session_manager = session.session_manager
run_agent = agent.run_agent
refresh_snapshot = snapshot.refresh_snapshot
