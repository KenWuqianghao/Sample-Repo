# Mobile / iMessage UX contract

The production path is **one user-visible reply per inbound message** (plus typing + tapbacks). The harness may print `{"type":"progress"}` JSON lines to **stdout**; [`modal_app/agent.py`](../modal_app/agent.py) logs those and does **not** forward them as iMessage bubbles.

## Signals

- **Typing:** `POST /typing` is turned on when work starts and off in `finally`.
- **Tapbacks:** best-effort reactions on the inbound `msg_id` (e.g. eyes at start, check / cross on completion). Linq may reject unknown reaction strings; failures are suppressed.
- **Threading:** every outbound text part uses the same `replyToMessageId` as the inbound job.

## Long replies

If the final text exceeds `HARNESS_MAX_REPLY_CHARS` (default 800), [`harness.format.split_for_imessage`](../harness/format.py) splits into multiple messages with `(i/n)` suffixes. There is still **no** mid-run “still working” chatter.

## Intents (one-word control)

Parsed from the **last** `[USER]:` line (see [`harness/intents.py`](../harness/intents.py)): `status`, `stop`, `pr`, `diff`, `tests`, `go`, etc. Those short-circuit the LLM when they map to a known intent.

## Webhook payloads

[`webhook/models.py`](../webhook/models.py) accepts optional `media` URLs and `message.reaction.added`. Jobs include `media_urls` for `--media-url` passed into `harness.run`.

## Sender allow-list

Optional env **`ALLOWED_SENDERS`**: comma-separated E.164 numbers. Set on **Modal `linq-secrets`** so the deployed FastAPI app sees it; non-listed senders are ignored with `{"ok": true}`.
