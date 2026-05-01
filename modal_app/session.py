"""Session manager: queue consumer, per-sender sandbox reuse, dispatch to run_agent."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, cast

import modal
from modal import FunctionCall

from modal_app.sandbox import spawn_sandbox
from modal_app.state import modal_app
from webhook.models import E164_RE

log = logging.getLogger(__name__)

SESSIONS = modal.Dict.from_name("agent-sessions", create_if_missing=True)
QUEUE = modal.Queue.from_name("linq-prompts", create_if_missing=True)

HISTORY_MAX_ENTRIES = 20  # 10 user/agent exchanges


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def trim_session_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(history) <= HISTORY_MAX_ENTRIES:
        return history
    return history[-HISTORY_MAX_ENTRIES:]


def should_respawn_sandbox(poll_result: int | None) -> bool:
    """``poll()`` returns an exit code when the sandbox main process has exited."""
    return poll_result is not None


def validate_e164(phone: str) -> bool:
    return bool(E164_RE.match(phone))


@modal_app.function(timeout=86400, min_containers=1)
def session_manager() -> None:
    from modal_app.agent import run_agent

    while True:
        try:
            job_obj = QUEUE.get(block=True, timeout=30.0)
        except Exception:
            log.debug("queue_idle_timeout")
            continue
        if job_obj is None:
            continue
        job = cast(dict[str, Any], job_obj)
        sender = cast(str, job["sender"])
        text = cast(str, job["text"])
        msg_id = cast(str, job["msg_id"])

        media_raw = job.get("media_urls", [])
        media_urls: list[str] = []
        if isinstance(media_raw, list):
            media_urls = [str(u) for u in media_raw if str(u).strip()]
        elif isinstance(media_raw, str):
            import json as _json

            try:
                parsed = _json.loads(media_raw)
                if isinstance(parsed, list):
                    media_urls = [str(u) for u in parsed]
            except _json.JSONDecodeError:
                media_urls = []

        if not validate_e164(sender):
            log.warning("invalid_sender_skipped sender=%s", sender)
            continue

        row_any = SESSIONS.get(sender)
        row: dict[str, Any] = cast(dict[str, Any], row_any) if isinstance(row_any, dict) else {}

        now = utc_now_iso()

        if not row:
            sb = spawn_sandbox(modal_app)
            row = {
                "sandbox_id": sb.object_id,
                "created_at": now,
                "last_active": now,
                "history": [],
            }
            SESSIONS[sender] = row
            log.info("session_created sender=%s sandbox_id=%s", sender, sb.object_id)
        else:
            sandbox_id = str(row.get("sandbox_id", ""))
            try:
                sb = modal.Sandbox.from_id(sandbox_id)
                if should_respawn_sandbox(sb.poll()):
                    log.warning("sandbox_dead_respawn sandbox_id=%s", sandbox_id)
                    sb = spawn_sandbox(modal_app)
                    row["sandbox_id"] = sb.object_id
                    row["last_active"] = now
                    SESSIONS[sender] = row
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "sandbox_lookup_failed_respawn sandbox_id=%s error=%s",
                    sandbox_id,
                    exc,
                )
                sb = spawn_sandbox(modal_app)
                row["sandbox_id"] = sb.object_id
                row["last_active"] = now
                SESSIONS[sender] = row

        row["last_active"] = now
        SESSIONS[sender] = row

        history = list(row.get("history", []))
        if not isinstance(history, list):
            history = []

        prev_spawn = row.get("active_spawn_id")
        if isinstance(prev_spawn, str) and prev_spawn:
            try:
                FunctionCall.from_id(prev_spawn).cancel()
                log.info("prior_run_cancelled sender=%s fc_id=%s", sender, prev_spawn)
            except Exception as exc:  # noqa: BLE001
                log.warning("prior_run_cancel_failed sender=%s err=%s", sender, exc)

        fc_handle = run_agent.spawn(
            str(row["sandbox_id"]),
            text,
            msg_id,
            sender,
            history,
            media_urls,
        )
        row["active_spawn_id"] = getattr(fc_handle, "object_id", None)
        SESSIONS[sender] = row


__all__ = [
    "SESSIONS",
    "QUEUE",
    "session_manager",
    "trim_session_history",
    "should_respawn_sandbox",
    "validate_e164",
    "utc_now_iso",
    "HISTORY_MAX_ENTRIES",
]
