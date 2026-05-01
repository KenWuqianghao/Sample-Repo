# Coding harness and updated architecture

Each prompt runs the **mobile-oriented tool loop** in [`harness/agent.py`](../harness/agent.py). [`harness/engine.py`](../harness/engine.py) is a thin wrapper that disables stdout JSON lines so tests stay quiet.

## Where it runs

- **Image**: [`modal_app/sandbox.py`](../modal_app/sandbox.py) copies [`harness/`](../harness/) into `/opt/vendor/harness`, sets `PYTHONPATH=/app:/opt/vendor`, and installs **`ripgrep`** for `search`.
- **Execution**: [`modal_app/agent.py`](../modal_app/agent.py) writes `/tmp/coding_prompt.txt`, then runs:

  `python -m <CODING_HARNESS_MODULE> --prompt-file ... --output-format json [--media-url ...]`

  Default module: **`harness.run`**.

## Model + tools

- If `MODEL_BASE_URL` is set (OpenAI-compatible **root**, e.g. `https://api.openai.com/v1`), the agent POSTs **`/v1/chat/completions`** with **`tools`** (read/write file, rg search, bounded shell, pytest, git helpers, GitHub draft PR / gist APIs).
- If unset: placeholder string so deploy wiring works without an LLM.
- **Modal UX**: sandbox env **`HARNESS_EMIT_FINAL_JSON_LINE=1`** is set by `run_agent` so stdout ends with `{"type":"final","result":...}`; the CLI disables that flag and prints legacy `{"result":...}`.

## Sandbox env (set by `run_agent`)

| Variable | Purpose |
|----------|---------|
| `HARNESS_AGENT_BRANCH` | Per-sender branch `agent/<sha8(phone)>` (prefix from `HARNESS_PR_BRANCH_PREFIX`) |
| `HARNESS_EMIT_FINAL_JSON_LINE` | `1` in Modal |
| `HARNESS_MAX_REPLY_CHARS` | Bubble split threshold (copied from parent env or default 800) |
| `HARNESS_AUTONOMY` | `branch_pr`: checkout agent branch before the LLM |

Workspace state: `/app/.harness/state.json` (see [`harness/state.py`](../harness/state.py)).

### Optional parent env (same secrets as webhook / Modal app)

Configure on **`model-secrets`** or FastAPI **`linq-secrets`** depending on visibility:

| Variable | Purpose |
|----------|---------|
| `HARNESS_MAX_REPLY_CHARS` | Default 800 |
| `HARNESS_PR_BRANCH_PREFIX` | Default `agent/` |
| `HARNESS_AUTONOMY` | Default `branch_pr` |
| `HARNESS_REPO_BASE_BRANCH` | Override GitHub PR base (else API default branch) |
| `ALLOWED_SENDERS` | Comma-separated E.164 (`linq-secrets`; empty = allow all) |

See also **[mobile-ux.md](./mobile-ux.md)**.

## Modal secret: `model-secrets`

| Variable | Purpose |
|----------|---------|
| `MODEL_BASE_URL` | OpenAI-compatible API root |
| `MODEL_API_KEY` or `OPENAI_API_KEY` | Bearer auth |
| `HARNESS_MODEL` | Model id |
| `HARNESS_HTTP_TIMEOUT_SECONDS` | Default 600 |
| `HARNESS_MAX_AGENT_STEPS` | Max LLM/tool rounds (default 32) |
| `CODING_HARNESS_MODULE` | Override CLI module (default `harness.run`) |

## “Local model” and Modal

Modal sandboxes cannot reach **`localhost`** on your laptop unless you expose it (tunnel, VPN, hosted endpoint). Options: tunnel, Modal-hosted model, or a public API.

## Modal token ID and token secret (CLI auth)

Same as before: **`modal token set --token-id ... --token-secret ...`** authenticate the Modal SDK. Unrelated to Linq or the LLM.
