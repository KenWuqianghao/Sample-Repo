"""Tool-using agent loop for the iMessage coding harness."""

from __future__ import annotations

import json
import os

import anthropic

from harness.intents import (
    extract_last_user_utterance,
    handle_intent,
    parse_intent,
)
from harness.policy import allow_tool_call
from harness.prompts import SYSTEM_IMESSAGE_AGENT, user_media_appendix
from harness.state import save_state, state_file_path, update_step
from harness.tools.registry import dispatch_tool, tools_anthropic_specs


def _emit(obj: dict, emit_progress: bool) -> None:
    if not emit_progress:
        return
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def run(
    prompt: str,
    *,
    emit_progress: bool = True,
    emit_final_json_line: bool | None = None,
    media_urls: list[str] | None = None,
) -> str:
    """Execute one inbound turn.

    Writes ``{"type":"progress", ...}`` lines to stdout when ``emit_progress``.

    When ``emit_final_json_line`` is true (or env ``HARNESS_EMIT_FINAL_JSON_LINE=1``),
    prints a terminating ``{"type":"final","result":...}`` line — used by Modal.
    CLI calls set ``emit_final_json_line=False`` and print ``{"result":...}`` themselves.
    """
    ef = (
        emit_final_json_line
        if emit_final_json_line is not None
        else (os.environ.get("HARNESS_EMIT_FINAL_JSON_LINE", "0") == "1")
    )

    def _maybe_final(payload: dict) -> None:
        if ef:
            print(json.dumps(payload, ensure_ascii=False), flush=True)

    last_user = extract_last_user_utterance(prompt)
    intent = parse_intent(last_user)

    if intent is not None:
        out = handle_intent(intent, state_path=state_file_path())
        if out is not None:
            _maybe_final({"type": "final", "result": out})
            return out

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        msg = (
            "Harness placeholder: set ANTHROPIC_API_KEY in the Modal secret `model-secrets`."
        )
        _maybe_final({"type": "final", "result": msg})
        return msg

    autonomy = os.environ.get("HARNESS_AUTONOMY", "branch_pr").strip()
    branch = os.environ.get("HARNESS_AGENT_BRANCH", "").strip()

    if autonomy == "branch_pr" and branch:
        from harness.tools import git_ops

        prep = git_ops.ensure_branch(branch)
        save_state({"branch": branch, "last_step": "ensure_branch"})
        _emit(
            {"type": "progress", "tool": "ensure_branch", "detail": prep[:800]},
            emit_progress,
        )

    user_content = prompt + user_media_appendix(media_urls or [])

    system = [
        {
            "type": "text",
            "text": SYSTEM_IMESSAGE_AGENT,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    messages: list[dict] = [{"role": "user", "content": user_content}]
    tools = tools_anthropic_specs()
    model = os.environ.get("HARNESS_MODEL", "claude-opus-4-7")
    max_steps = int(os.environ.get("HARNESS_MAX_AGENT_STEPS", "32"))

    client = anthropic.Anthropic(api_key=api_key)

    for step in range(max_steps):
        update_step(f"llm_step_{step}")

        try:
            response = client.messages.create(
                model=model,
                max_tokens=8192,
                system=system,
                messages=messages,
                tools=tools,
                thinking={"type": "adaptive"},
            )
        except anthropic.APIError as exc:
            err = f"Model API error: {exc}"
            _maybe_final({"type": "final", "result": err})
            return err

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        # Preserve all content blocks (including thinking) for the next turn.
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "tool_use":
            tool_results = []
            for tc in tool_use_blocks:
                name = tc.name
                args = tc.input if isinstance(tc.input, dict) else {}
                ok, denial = allow_tool_call(name, json.dumps(args))
                if not ok:
                    observation = f"policy denied {name}: {denial}"
                else:
                    try:
                        observation = dispatch_tool(name, args)
                    except Exception as exc:  # noqa: BLE001
                        observation = f"tool error ({name}): {exc}"
                    else:
                        if name == "open_draft_pr" and observation.startswith("http"):
                            save_state({"last_pr_url": observation, "last_step": "opened_pr"})
                        if name == "create_gist" and observation.startswith("http"):
                            save_state({"last_gist_url": observation, "last_step": "created_gist"})

                _emit({"type": "progress", "tool": name, "step": step}, emit_progress)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": observation[:120_000],
                    }
                )

            messages.append({"role": "user", "content": tool_results})
            continue

        if response.stop_reason in ("end_turn", "max_tokens"):
            final = "\n".join(b.text for b in text_blocks).strip()
            if not final:
                final = "(no output)"
            save_state({"last_step": "done"})
            _maybe_final({"type": "final", "result": final})
            return final

        err = f"Unexpected model stop (stop_reason={response.stop_reason!r})"
        _maybe_final({"type": "final", "result": err})
        return err

    overflow = (
        "Stopped early: exceeded HARNESS_MAX_AGENT_STEPS. "
        "Open a gist or shorten the task; sandbox state preserved."
    )
    save_state({"last_step": "max_steps"})
    _maybe_final({"type": "final", "result": overflow})
    return overflow
