"""Unit tests for LinqClient (httpx + respx)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from linq.client import LinqAPIError, LinqClient


@respx.mock
async def test_send_message_and_traceparent() -> None:
    route = respx.post("https://api.linqapp.com/api/partner/v3/messages").mock(
        return_value=httpx.Response(200, json={"id": "out_1"})
    )
    async with httpx.AsyncClient() as http:
        client = LinqClient("tok", "+18005551234", client=http)
        out = await client.send_message("+16505550100", "hi", reply_to_message_id="in_1")
        assert out["id"] == "out_1"
    assert route.called
    sent = route.calls.last.request
    assert sent.headers["authorization"] == "Bearer tok"
    tp = sent.headers.get("traceparent", "")
    assert tp.startswith("00-") and tp.endswith("-01")
    body = json.loads(sent.content.decode())
    assert body["from"] == "+18005551234"
    assert body["to"] == "+16505550100"
    assert body["replyToMessageId"] == "in_1"


@respx.mock
async def test_send_typing_active_toggle() -> None:
    r1 = respx.post("https://api.linqapp.com/api/partner/v3/typing").mock(
        return_value=httpx.Response(204)
    )
    async with httpx.AsyncClient() as http:
        c = LinqClient("t", "+18005551234", client=http)
        await c.send_typing("+16505550100", True)
        await c.send_typing("+16505550100", False)
    assert r1.call_count == 2
    bodies = [json.loads(c.request.content.decode()) for c in r1.calls]
    assert bodies[0] == {"to": "+16505550100", "active": True}
    assert bodies[1] == {"to": "+16505550100", "active": False}


@respx.mock
async def test_send_reaction_path() -> None:
    rx = respx.post(
        "https://api.linqapp.com/api/partner/v3/messages/msg_abc/reactions",
    ).mock(return_value=httpx.Response(204))
    async with httpx.AsyncClient() as http:
        c = LinqClient("t", "+1", client=http)
        await c.send_reaction("msg_abc", "👍")
    assert rx.called
    assert json.loads(rx.calls.last.request.content.decode()) == {"reaction": "👍"}


@respx.mock
async def test_send_messages_multipart_returns_last_id() -> None:
    msgs = respx.post("https://api.linqapp.com/api/partner/v3/messages").mock(
        side_effect=[
            httpx.Response(200, json={"id": "a"}),
            httpx.Response(200, json={"id": "b"}),
        ],
    )

    async with httpx.AsyncClient() as http:
        c = LinqClient("t", "+18005551410", client=http)

        last = await c.send_messages_multipart(
            "+16505550100", ["one", "two"], reply_to_message_id="m0"
        )

    assert last == "b"
    assert msgs.call_count == 2


@respx.mock
async def test_get_conversation_params() -> None:
    rx = respx.get(
        url__startswith="https://api.linqapp.com/api/partner/v3/conversations",
    ).mock(
        return_value=httpx.Response(200, json={"items": []}),
    )
    async with httpx.AsyncClient() as http:
        c = LinqClient("t", "+1", client=http)
        data = await c.get_conversation("+16505550100")
    assert data == {"items": []}
    q = rx.calls.last.request.url.params.get("participant")
    assert q == "+16505550100"


@respx.mock
async def test_non_2xx_raises() -> None:
    respx.post("https://api.linqapp.com/api/partner/v3/messages").mock(
        return_value=httpx.Response(500, text="nope"),
    )
    async with httpx.AsyncClient() as http:
        c = LinqClient("t", "+1", client=http)
        with pytest.raises(LinqAPIError) as ei:
            await c.send_message("+1", "x")
        assert ei.value.status_code == 500
        assert "nope" in ei.value.message
