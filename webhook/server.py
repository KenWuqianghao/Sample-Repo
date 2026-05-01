"""FastAPI Linq webhook receiver."""

from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import modal
import structlog
from fastapi import FastAPI, HTTPException, Request
from httpx import AsyncClient
from linq.client import LinqClient

from webhook.models import E164_RE
from webhook.payload_normalize import parse_linq_webhook
from webhook.verification import verify_linq_signature

log = structlog.get_logger(__name__)



def _mask_signature(sig: str | None) -> str:
    if not sig:
        return "<empty>"
    if len(sig) <= 10:
        return f"{sig[:3]}…"
    return f"{sig[:8]}…{sig[-4:]}"


def _prompts_queue(app: FastAPI) -> modal.Queue:
    q: modal.Queue | None = getattr(app.state, "prompts_queue", None)
    if q is None:
        q = modal.Queue.from_name("linq-prompts", create_if_missing=True)
        app.state.prompts_queue = q
    return q


def create_app(
    *,
    linq_client_factory: Callable[[AsyncClient], LinqClient | None] | None = None,
    load_env: bool = True,
) -> FastAPI:
    if load_env:
        from dotenv import load_dotenv

        load_dotenv()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        http = AsyncClient(timeout=10.0)
        app.state.http = http

        def default_factory(c: AsyncClient) -> LinqClient | None:
            import os

            token = os.environ.get("LINQ_TOKEN")
            from_no = os.environ.get("LINQ_FROM_NUMBER")
            if not token or not from_no:
                return None
            return LinqClient(token, from_no, client=c)

        if linq_client_factory is not None:
            app.state.linq = linq_client_factory(http)
        else:
            app.state.linq = default_factory(http)

        # Spawn the queue-consuming session_manager so it starts draining
        # linq-prompts as soon as the web worker is live.
        try:
            from modal_app.session import session_manager as _sm
            _sm.spawn()
            log.info("session_manager_spawned")
        except Exception as _exc:
            log.warning("session_manager_spawn_failed", error=str(_exc))

        try:
            yield
        finally:
            linq = app.state.linq
            if linq is not None:
                await linq.aclose()
            await http.aclose()

    app = FastAPI(lifespan=lifespan, title="Linq Webhook")

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": "imessage-coding-agent", "health": "/health", "webhook": "/linq/webhook"}

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @app.post("/linq/webhook")
    async def linq_webhook(request: Request) -> dict[str, bool]:
        import os

        body = await request.body()
        secret = os.environ.get("LINQ_SECRET", "")
        sig = request.headers.get("X-Webhook-Signature")
        ts = request.headers.get("X-Webhook-Timestamp")
        if not verify_linq_signature(body, sig, secret, timestamp=ts):
            log.warning("webhook_signature_invalid", signature=_mask_signature(sig))
            raise HTTPException(status_code=401, detail="invalid signature")

        try:
            event, msg = parse_linq_webhook(body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="invalid json") from None

        raw_allow = os.environ.get("ALLOWED_SENDERS", "").strip()

        allowed_phones: set[str] | None
        if raw_allow:
            allowed_phones = {p.strip() for p in raw_allow.split(",") if p.strip()}
        else:
            allowed_phones = None

        def enqueue_ok(sender_phone: str) -> bool:
            if not E164_RE.match(sender_phone):
                raise HTTPException(status_code=400, detail="invalid E.164 sender")

            if allowed_phones is not None and sender_phone not in allowed_phones:
                log.warning("sender_not_allowed sender=%s", sender_phone)
                return False
            return True

        if event in (
            "reaction.added",
            "reaction.removed",
            "message.reaction.added",
        ):
            if msg is None:
                return {"ok": True}
            reaction = msg.reaction or ""
            sender_rx = msg.from_
            if not enqueue_ok(sender_rx):
                return {"ok": True}
            rx_mid = msg.reply_to_message_id or msg.id
            if not rx_mid:
                return {"ok": True}
            rx_job: dict[str, Any] = {
                "kind": "reaction",
                "sender": sender_rx,
                "text": f"[REACTION:{reaction}]",
                "msg_id": rx_mid,
                "media_urls": [],
            }

            await _prompts_queue(request.app).put.aio(rx_job)

            return {"ok": True}

        if event != "message.received":
            return {"ok": True}
        if msg is None:
            return {"ok": True}

        sender = msg.from_
        if not enqueue_ok(sender):
            return {"ok": True}

        media_urls = [m.url for m in (msg.media or []) if m.url]
        text_body = (msg.text or "").strip()
        if not text_body and media_urls:
            text_body = "[media attachment]"

        if not text_body and not media_urls:
            return {"ok": True}

        mid = msg.id

        if not mid:
            return {"ok": True}

        msg_job: dict[str, Any] = {
            "kind": "message",
            "sender": sender,
            "text": text_body,
            "msg_id": mid,
            "media_urls": media_urls,
        }
        await _prompts_queue(request.app).put.aio(msg_job)
        return {"ok": True}

    return app


app = create_app()


__all__ = ["app", "create_app", "E164_RE"]
