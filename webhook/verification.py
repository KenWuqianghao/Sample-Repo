"""HMAC verification for Linq webhooks."""

from __future__ import annotations

import hashlib
import hmac


def verify_linq_signature(
    payload_bytes: bytes,
    signature_header: str | None,
    secret: str,
    *,
    timestamp: str | None = None,
) -> bool:
    """
    Verify Linq Partner webhook signatures (HMAC-SHA256).

    Per Linq docs, the signed material is: ``f"{timestamp}.{raw_body}"`` encoded as UTF-8
    where ``raw_body`` is the exact request body bytes.

    Header format: hex digest, optionally prefixed with ``sha256=``.

    Uses hmac.compare_digest for timing-safe comparison. Never raises; returns False on failure.
    """
    if not signature_header or not timestamp or not secret:
        return False
    sig = signature_header.removeprefix("sha256=").strip()
    message = timestamp.encode("utf-8") + b"." + payload_bytes
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
