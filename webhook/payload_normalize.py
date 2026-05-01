"""Normalize Linq Partner API v3 webhooks to internal LinqMessageData.

v3 uses ``event_type`` (not ``event``) and MessageEventV2 / ReactionEventBase shapes;
see https://docs.linqapp.com/guides/resources/migration-v2-to-v3/
"""

from __future__ import annotations

import json
from typing import Any

from webhook.models import LinqMediaItem, LinqMessageData


def _extract_handle(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        v = data.get(key)
        if isinstance(v, dict):
            h = v.get("handle")
            if isinstance(h, str) and h.strip():
                return h.strip()
        elif isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _text_from_parts(parts: list[Any] | None) -> str:
    if not parts:
        return ""
    chunks: list[str] = []
    for p in parts:
        if not isinstance(p, dict):
            continue
        if p.get("type") == "text":
            val = p.get("value")
            if isinstance(val, str) and val:
                chunks.append(val)
    return "\n".join(chunks).strip()


def _media_from_parts(parts: list[Any] | None) -> list[LinqMediaItem]:
    if not parts:
        return []
    out: list[LinqMediaItem] = []
    for p in parts:
        if not isinstance(p, dict):
            continue
        if p.get("type") == "media" and p.get("url"):
            out.append(
                LinqMediaItem(url=str(p["url"]), type=str(p.get("mime_type") or "") or None)
            )
    return out


def _legacy_media(data: dict[str, Any]) -> list[LinqMediaItem]:
    raw = data.get("media")
    if not isinstance(raw, list):
        return []
    out: list[LinqMediaItem] = []
    for item in raw:
        if isinstance(item, dict) and item.get("url"):
            out.append(
                LinqMediaItem(url=str(item["url"]), type=str(item.get("type") or "") or None)
            )
    return out


def _normalize_reaction(data: dict[str, Any]) -> LinqMessageData | None:
    sender = _extract_handle(data, "from_handle") or str(data.get("from") or "")
    msg_id = str(data.get("message_id") or data.get("id") or "")
    custom = data.get("custom_emoji")
    rtype = data.get("reaction_type")
    if custom:
        reaction = str(custom)
    elif rtype is not None:
        reaction = str(rtype)
    else:
        reaction = ""
    if not sender and not msg_id:
        return None
    return LinqMessageData(
        id=msg_id,
        from_=sender,
        reaction=reaction,
    )


def _normalize_message_body(
    data: dict[str, Any],
) -> LinqMessageData | None:
    # Skip outbound / our own messages (v3 direction + legacy is_from_me).
    if data.get("direction") == "outbound":
        return None
    if data.get("is_from_me") is True:
        return None

    parts = data.get("parts") if isinstance(data.get("parts"), list) else None
    text = _text_from_parts(parts)
    if not text and isinstance(data.get("text"), str):
        text = data["text"].strip()

    media = _media_from_parts(parts) if parts else []
    if not media:
        media = _legacy_media(data)

    msg_id = str(data.get("id") or "")
    sender = _extract_handle(data, "sender_handle", "from_handle") or str(data.get("from") or "")

    reply_to = data.get("replyToMessageId") or data.get("reply_to_message_id")
    rt = data.get("reply_to")
    if not reply_to and isinstance(rt, dict):
        mid = rt.get("message_id")
        if mid:
            reply_to = str(mid)

    proto = data.get("protocol")
    if not isinstance(proto, str):
        svc = data.get("service")
        proto = str(svc) if isinstance(svc, str) else None

    if not msg_id and not text and not media:
        return None

    return LinqMessageData(
        id=msg_id,
        from_=sender,
        to=str(data["to"]) if isinstance(data.get("to"), str) else None,
        protocol=proto,
        text=text or None,
        media=media or None,
        reaction=None,
        reply_to_message_id=str(reply_to) if reply_to else None,
    )


def parse_linq_webhook(body: bytes) -> tuple[str, LinqMessageData | None]:
    """Return ``(event_type, normalized message data or None)``.

    ``event`` is from ``event_type`` (v3) or ``event`` (legacy). For non-message payloads
    (e.g. chat metadata only), ``data`` is None.
    """
    raw: dict[str, Any] = json.loads(body)
    event = str(raw.get("event_type") or raw.get("event") or "")
    dr = raw.get("data")
    if not isinstance(dr, dict):
        return event, None

    if event in ("reaction.added", "reaction.removed", "message.reaction.added"):
        return event, _normalize_reaction(dr)

    if event.startswith("message."):
        return event, _normalize_message_body(dr)

    return event, None


__all__ = ["parse_linq_webhook"]
