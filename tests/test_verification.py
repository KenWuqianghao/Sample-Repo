"""Unit tests for webhook HMAC verification."""

from __future__ import annotations

import hashlib
import hmac

from webhook.verification import verify_linq_signature


def _sign(body: bytes, secret: str, ts: str) -> str:
    msg = ts.encode("utf-8") + b"." + body
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def test_valid_signature_passes() -> None:
    secret = "whsec_test"
    ts = "1714589045"
    body = b'{"event":"message.received","data":{}}'
    sig = _sign(body, secret, ts)
    assert verify_linq_signature(body, sig, secret, timestamp=ts) is True
    assert verify_linq_signature(body, f"sha256={sig}", secret, timestamp=ts) is True


def test_wrong_secret_fails() -> None:
    body = b"{}"
    ts = "1"
    sig = _sign(body, "correct", ts)
    assert verify_linq_signature(body, sig, "wrong", timestamp=ts) is False


def test_tampered_body_fails() -> None:
    secret = "whsec_x"
    ts = "99"
    body = b'{"ok":true}'
    sig = _sign(body, secret, ts)
    tampered = b'{"ok":false}'
    assert verify_linq_signature(tampered, sig, secret, timestamp=ts) is False


def test_missing_header_returns_false() -> None:
    assert verify_linq_signature(b"{}", None, "s", timestamp="1") is False
    assert verify_linq_signature(b"{}", "", "s", timestamp="1") is False


def test_missing_timestamp_returns_false() -> None:
    assert verify_linq_signature(b"{}", "abc", "s", timestamp=None) is False
    assert verify_linq_signature(b"{}", "abc", "s", timestamp="") is False
