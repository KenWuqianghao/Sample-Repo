"""Tests for Linq v3 webhook normalization."""

from __future__ import annotations

import json

from webhook.payload_normalize import parse_linq_webhook


def test_v3_message_received_2026_minimal() -> None:
    body = {
        "api_version": "v3",
        "webhook_version": "2026-02-03",
        "event_type": "message.received",
        "event_id": "e1",
        "data": {
            "id": "msg-1",
            "direction": "inbound",
            "sender_handle": {"handle": "+16505550100", "id": "h1", "service": "iMessage"},
            "parts": [{"type": "text", "value": "Hello"}],
            "service": "iMessage",
        },
    }
    event, data = parse_linq_webhook(json.dumps(body).encode())
    assert event == "message.received"
    assert data is not None
    assert data.id == "msg-1"
    assert data.from_ == "+16505550100"
    assert data.text == "Hello"


def test_v3_message_skips_outbound() -> None:
    body = {
        "event_type": "message.received",
        "data": {
            "id": "m2",
            "direction": "outbound",
            "sender_handle": {"handle": "+16505550100"},
            "parts": [{"type": "text", "value": "me"}],
        },
    }
    _, data = parse_linq_webhook(json.dumps(body).encode())
    assert data is None


def test_v3_reaction_added() -> None:
    body = {
        "event_type": "reaction.added",
        "data": {
            "message_id": "msg-rx",
            "reaction_type": "like",
            "from_handle": {"handle": "+16505550101"},
        },
    }
    event, data = parse_linq_webhook(json.dumps(body).encode())
    assert event == "reaction.added"
    assert data is not None
    assert data.from_ == "+16505550101"
    assert data.id == "msg-rx"
    assert data.reaction == "like"


def test_chat_only_data_returns_none_message() -> None:
    body = {
        "api_version": "v3",
        "event_type": "message.received",
        "data": {
            "chat": {
                "id": "c1",
                "owner_handle": {"handle": "+1", "service": "iMessage"},
            },
        },
    }
    event, data = parse_linq_webhook(json.dumps(body).encode())
    assert event == "message.received"
    assert data is None


def test_legacy_event_key_still_works() -> None:
    body = {
        "event": "message.received",
        "data": {
            "id": "old",
            "from": "+16505550102",
            "text": "legacy",
        },
    }
    event, data = parse_linq_webhook(json.dumps(body).encode())
    assert event == "message.received"
    assert data is not None
    assert data.text == "legacy"
    assert data.from_ == "+16505550102"
