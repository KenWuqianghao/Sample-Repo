"""Coding harness runner inside a Modal Sandbox + Linq replies."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from contextlib import suppress
from typing import Any

import modal
from harness.format import split_for_imessage
from linq.client import LinqAPIError, LinqClient

from modal_app.session import SESSIONS, trim_session_history, utc_now_iso
from modal_app.state import modal_app

log = logging.getLogger(__name__)

PROMPT_PATH = "/tmp/coding_prompt.txt"


def build_full_prompt(current: str, history: list[dict[str, Any]]) -> str:
    """Include the last 10 history entries (5 user/agent exchanges) plus the latest user message."""
    tail = history[-10:]
    parts: list[str] = []
    for item in tail:
        role = str(item.get("role", "user"))
        content = str(item.get("content", ""))
        parts.append(f"[{role.upper()}]: {content}")
    parts.append(f"[USER]: {current}")
    return "\n".join(parts)


def parse_agent_output(lines: list[str]) -> str:
    """Prefer harness ``type=final`` JSON; fall back to legacy shapes."""
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("{"):
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if data.get("type") == "final":
                val = data.get("result")
                if isinstance(val, str) and val.strip():
                    return val.strip()
            for key in ("result", "response", "message", "content", "text", "output"):
                val = data.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
            try:
                return json.dumps(data, indent=2)[:15000]
            except Exception:  # noqa: BLE001
                return stripped[:15000]

    joined = "\n".join(lines).strip()
    return joined or "(no output)"


def _append_history(
    sender: str,
    user_text: str,
    inbound_msg_id: str,
    agent_text: str,
    outbound_msg_id: str | None,
) -> None:
    row_any = SESSIONS.get(sender)
    if not isinstance(row_any, dict):
        return
    row: dict[str, Any] = dict(row_any)
    hist_any = row.get("history", [])
    history: list[dict[str, Any]] = list(hist_any) if isinstance(hist_any, list) else []
    history.append({"role": "user", "content": user_text, "msg_id": inbound_msg_id})
    history.append({"role": "agent", "content": agent_text, "msg_id": outbound_msg_id})
    row["history"] = trim_session_history(history)
    row["last_active"] = utc_now_iso()
    SESSIONS[sender] = row


def cast_history_item(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": str(raw.get("role", "user")),
        "content": str(raw.get("content", "")),
        "msg_id": raw.get("msg_id"),
    }


@modal_app.function(timeout=3600)
async def run_agent(
    sandbox_id: str,
    prompt: str,
    msg_id: str,
    sender: str,
    history: list[Any],
    media_urls: list[str] | None = None,
) -> None:
    sandbox = await modal.Sandbox.from_id.aio(sandbox_id)
    linq = LinqClient(os.environ["LINQ_TOKEN"], os.environ["LINQ_FROM_NUMBER"])
    hist = [cast_history_item(h) for h in history if isinstance(h, dict)]

    max_reply = int(os.environ.get("HARNESS_MAX_REPLY_CHARS", "800"))
    branch_prefix = os.environ.get("HARNESS_PR_BRANCH_PREFIX", "agent/")
    hsh = hashlib.sha256(sender.encode()).hexdigest()[:8]
    agent_branch = f"{branch_prefix.rstrip('/')}/{hsh}"

    result_text = ""
    success = False
    outbound_last: str | None = None

    try:
        with suppress(LinqAPIError):
            await linq.send_typing(sender, True)
        with suppress(LinqAPIError):
            await linq.send_reaction(msg_id, "👀")

        full_prompt = build_full_prompt(prompt, hist)
        with sandbox.open(PROMPT_PATH, "w") as f:
            f.write(full_prompt)

        harness_mod = os.environ.get("CODING_HARNESS_MODULE", "harness.run").strip()

        cmd: list[str] = [
            "python",
            "-m",
            harness_mod,
            "--prompt-file",
            PROMPT_PATH,
            "--output-format",
            "json",
        ]
        for url in media_urls or []:
            if url:
                cmd.extend(["--media-url", url])

        exec_env: dict[str, str] = {
            "HARNESS_EMIT_FINAL_JSON_LINE": "1",
            "HARNESS_AGENT_BRANCH": agent_branch,
            "HARNESS_SENDER_E164": sender,
            "HARNESS_MAX_REPLY_CHARS": str(max_reply),
            "HARNESS_AUTONOMY": os.environ.get("HARNESS_AUTONOMY", "branch_pr"),
        }
        # Explicitly forward API credentials so the harness exec'd inside the sandbox
        # sees the same values as run_agent (both share model-secrets, but being
        # explicit prevents surprises if Modal exec env inheritance changes).
        for _key in ("ANTHROPIC_API_KEY", "HARNESS_MODEL"):
            _val = os.environ.get(_key)
            if _val:
                exec_env[_key] = _val

        proc = sandbox.exec(*cmd, env=exec_env, bufsize=1)

        result_lines: list[str] = []
        for line in proc.stdout:
            line = line.strip() if isinstance(line, str) else str(line).strip()
            if not line:
                continue
            result_lines.append(line)
            if line.startswith("{"):
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if payload.get("type") == "progress":
                    log.info("harness_progress %s", payload)

        proc.wait()
        code = proc.returncode

        if code != 0:
            stderr_chunks: list[str] = []
            for err_line in proc.stderr:
                stderr_chunks.append(err_line if isinstance(err_line, str) else str(err_line))
            err_text = "".join(stderr_chunks).replace("\n", " ")[:280]
            result_text = f"Run failed (exit {code}). {err_text or 'see Modal logs.'}"
            success = False
        else:
            result_text = parse_agent_output(result_lines)
            success = True

        parts = split_for_imessage(result_text, max_len=max_reply)
        outbound_last = await linq.send_messages_multipart(
            sender,
            parts,
            reply_to_message_id=msg_id,
        )

        with suppress(LinqAPIError):
            await linq.send_reaction(msg_id, "✅" if success else "❌")

        _append_history(sender, prompt, msg_id, result_text, outbound_last)

    except LinqAPIError as exc:
        log.error(
            "linq_api_error status=%s: %s",
            exc.status_code,
            exc.message,
            exc_info=True,
        )
        with suppress(LinqAPIError):
            await linq.send_message(
                sender,
                "Sorry, something went wrong on my end. Try again in a moment.",
                reply_to_message_id=msg_id,
            )

    except Exception:
        log.exception("run_agent_unexpected")
        with suppress(LinqAPIError):
            await linq.send_message(
                sender,
                "Sorry, something went wrong on my end. Try again in a moment.",
                reply_to_message_id=msg_id,
            )

    finally:
        with suppress(LinqAPIError):
            await linq.send_typing(sender, False)
        await linq.aclose()


__all__ = ["run_agent", "build_full_prompt", "parse_agent_output", "cast_history_item"]
