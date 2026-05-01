"""Async Linq Partner API client."""

from __future__ import annotations

import secrets
from typing import Any, Literal
from urllib.parse import quote

import httpx
import structlog

from linq.models import (
    SendMessageRequest,
    SendReactionRequest,
    SendTypingRequest,
)

log = structlog.get_logger(__name__)

Protocol = Literal["imessage", "rcs", "sms"]


class LinqAPIError(Exception):
    """Raised when Linq returns a non-success HTTP status."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Linq API error {status_code}: {message}")


def _make_traceparent() -> str:
    """W3C traceparent: version-trace_id-parent_id-flags."""
    trace_id = secrets.token_hex(16)
    span_id = secrets.token_hex(8)
    return f"00-{trace_id}-{span_id}-01"


class LinqClient:
    BASE_URL = "https://api.linqapp.com/api/partner/v3"

    def __init__(
        self,
        token: str,
        from_number: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = token
        self._from_number = from_number
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=10.0)

    def _headers(self) -> dict[str, str]:
        traceparent = _make_traceparent()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "traceparent": traceparent,
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        url = f"{self.BASE_URL}{path}"
        headers = self._headers()
        log.debug("linq_request", method=method, url=url, traceparent=headers["traceparent"])
        resp = await self._client.request(
            method,
            url,
            headers=headers,
            json=json_body,
            params=params,
        )
        if resp.status_code >= 400:
            raise LinqAPIError(resp.status_code, resp.text)
        return resp

    async def send_message(
        self,
        to: str,
        text: str,
        protocol: Protocol = "imessage",
        reply_to_message_id: str | None = None,
    ) -> dict[str, Any]:
        body = SendMessageRequest.model_validate(
            {
                "from": self._from_number,
                "to": to,
                "text": text,
                "protocol": protocol,
                "replyToMessageId": reply_to_message_id,
            }
        )
        resp = await self._request("POST", "/messages", json_body=body.model_dump(by_alias=True))
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        if not isinstance(data, dict):
            return {"data": data}
        return data

    async def send_messages_multipart(
        self,
        to: str,
        parts: list[str],
        *,
        protocol: Protocol = "imessage",
        reply_to_message_id: str | None = None,
    ) -> str | None:
        """Send multiple text bubbles sequentially; returns last outbound message id."""
        last_id: str | None = None
        for part in parts:
            if not part:
                continue
            resp = await self.send_message(
                to,
                part,
                protocol=protocol,
                reply_to_message_id=reply_to_message_id,
            )
            if isinstance(resp, dict):
                oid = resp.get("id")
                last_id = str(oid) if oid is not None else last_id
        return last_id

    async def send_typing(self, to: str, active: bool) -> None:
        body = SendTypingRequest(to=to, active=active)
        await self._request("POST", "/typing", json_body=body.model_dump())

    async def send_reaction(self, message_id: str, reaction: str) -> None:
        body = SendReactionRequest(reaction=reaction)
        await self._request(
            "POST",
            f"/messages/{quote(message_id, safe='')}/reactions",
            json_body=body.model_dump(),
        )

    async def get_conversation(self, phone: str) -> dict[str, Any]:
        resp = await self._request("GET", "/conversations", params={"participant": phone})
        data = resp.json()
        if not isinstance(data, dict):
            return {"value": data}
        return data

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
