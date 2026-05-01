# iMessage Coding Agent

Ramp-style background agent: **Linq** delivers iMessage webhooks, **FastAPI** verifies and enqueues work, **Modal** runs a **session manager** and **per-sender sandboxes** that execute a **custom coding harness** (your model + tools), then replies via Linq with threading and typing indicators.

See **[docs/coding-harness.md](docs/coding-harness.md)** and **[docs/mobile-ux.md](docs/mobile-ux.md)** for the tool harness, **`model-secrets`**, sender allow-list, and iMessage UX.

## Architecture

```
┌─────────────┐     iMessage      ┌──────────────┐    POST webhook     ┌─────────────────────┐
│ User iPhone │ ───────────────► │  Linq API    │ ──────────────────► │ FastAPI on Modal     │
└─────────────┘                  └──────────────┘                     │ POST /linq/webhook   │
       ▲                                ▲                             └──────────┬──────────┘
       │                                │ HMAC verify + Queue.put                      │
       │                                │                                            ▼
       │                                │                               ┌─────────────────────┐
       │                                └─────────────────────────────── │ modal.Queue          │
       │                                                                   │  (linq-prompts)     │
       │                                                                   └──────────┬──────────┘
       │                                                                              │ get()
       │                                                                              ▼
       │                                ┌──────────────────┐            ┌─────────────────────┐
       │                                │ modal.Dict        │◄─────────── │ session_manager      │
       │                                │ (agent-sessions)  │            │ spawn / reuse Sandbox │
       │                                └──────────────────┘            └──────────┬──────────┘
       │                                                                             │ spawn
       │                                                                             ▼
       │                                ┌──────────────────┐            ┌─────────────────────┐
       │                                │ harness (Python) │◄────────── │ run_agent            │
       │                                │ + your model     │            │ exec + Linq reply    │
       │                                └──────────────────┘            └─────────────────────┘
       │                                                                             │
       └─────────────────────────────────────────────────────────────────────────────┘
                                         threaded reply (replyToMessageId)

Every 30 minutes, `refresh_snapshot` updates the cloned GitHub repo in a sandbox and publishes a new
filesystem snapshot (`modal.Dict` `snapshot-meta`) so cold starts stay fast.
```

## Prerequisites

- **Modal** account and CLI (`modal token set` — see [docs/coding-harness.md](docs/coding-harness.md))
- **Linq** Partner API (Bearer token, webhook signing secret, **from** number)
- **Model endpoint** reachable from Modal (URL + optional API key), or customize [`harness/agent.py`](harness/agent.py)
- **GitHub** token + `REPO_URL` for the sandbox image clone

## Setup (exact order)

1. Clone this repo and enter the directory.

2. Install dependencies:

   ```bash
   uv sync
   ```

   (or `pip install -e ".[dev]"` in a virtualenv.)

3. Authenticate Modal:

   ```bash
   modal token set --token-id ... --token-secret ...
   ```

4. Create Modal secrets (cloud runs use these; **`.env` is not read on Modal** unless you copy values into secrets):

   ```bash
   modal secret create linq-secrets LINQ_TOKEN=... LINQ_SECRET=... LINQ_FROM_NUMBER=...
   # Optional allow-list (comma-separated E.164), same secret:
   # modal secret create linq-secrets ... ALLOWED_SENDERS=+15551234567 --force

   modal secret create model-secrets MODEL_BASE_URL=... MODEL_API_KEY=... HARNESS_MODEL=...
   modal secret create github-token GITHUB_TOKEN=... REPO_URL=... --force
   ```

   To sync from a local file: `modal secret create linq-secrets --from-dotenv .env --force` (ensure the file has the three `LINQ_*` keys).

   `MODEL_BASE_URL` can be omitted initially (harness returns a placeholder).

5. Deploy:

   ```bash
   make -C deploy deploy
   ```

   Webhook base URL is printed for `fastapi_app`. Register with Linq:

   **`https://<that-host>/linq/webhook`**

6. Run the session manager worker, e.g.:

   ```bash
   modal run modal_app/app.py::session_manager
   ```

Copy `.env.example` to `.env` for **local** `make serve` / Linq test tunnels only.

## Testing locally

```bash
make -C deploy serve    # FastAPI
make -C deploy tunnel   # optional public URL
make -C deploy test     # pytest
```

## How it works (by layer)

1. **Linq** — Inbound events, outbound messages, typing, threading.
2. **Webhook** — Raw body HMAC verify, enqueue `modal.Queue`, fast `{"ok": true}`.
3. **Session manager** — Reuse `modal.Sandbox` per sender; respawn if dead; `run_agent.spawn(...)`.
4. **Agent** — Writes prompt file, runs `python -m harness.run` (or `CODING_HARNESS_MODULE`), parses JSON stdout, replies via Linq, updates `modal.Dict` history.
5. **Snapshot cron** — Refreshes `/app` git checkout and publishes a filesystem snapshot image.

## Logs

```bash
make -C deploy tail
```

## Deviations from the original design doc

- **Agent backend** — Custom **`harness/agent.py`** tool loop (+ `engine.py` shim); model via `MODEL_BASE_URL`.
- **Webhook signing** — `X-Webhook-Signature` + `X-Webhook-Timestamp` per Linq docs.
- **Secrets** — `model-secrets` replaces `openai-key` for the sandbox (LLM / harness env).
- **Modal API** — `min_containers`, `snapshot_filesystem()` snapshot refresh, etc., as implemented in `modal_app/`.

## License

Proprietary / your org — add a `LICENSE` if you open-source.
