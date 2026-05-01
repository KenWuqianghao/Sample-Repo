"""Tool schemas (OpenAI and Anthropic formats) and dispatch."""

from __future__ import annotations

from typing import Any

from harness.tools import fs, git_ops, shell, tests
from harness.tools import github_api as ghapi

_TOOL_DEFS: list[tuple[str, str, dict[str, dict[str, Any]], list[str]]] = [
    (
        "read_file",
        "Read a UTF-8 text file under the workspace (/app)",
        {"path": {"type": "string", "description": "Repo-relative path"}},
        ["path"],
    ),
    (
        "write_file",
        "Create or overwrite a text file",
        {"path": {"type": "string"}, "content": {"type": "string"}},
        ["path", "content"],
    ),
    (
        "search",
        "Search with ripgrep",
        {"pattern": {"type": "string"}, "subdir": {"type": "string", "default": "."}},
        ["pattern"],
    ),
    (
        "run_shell",
        "Run a shell command inside /app (policy-restricted)",
        {
            "command": {"type": "string"},
            "timeout_seconds": {"type": "integer", "default": 120},
        },
        ["command"],
    ),
    (
        "run_tests",
        "Run pytest (target optional)",
        {
            "target": {"type": "string", "description": "Path or pytest args"},
            "verbose": {"type": "boolean", "description": "If true, drop -q"},
        },
        [],
    ),
    ("git_status", "Porcelain git status summary", {}, []),
    ("git_diff_stat", "Git diff --stat HEAD vs working tree changes", {}, []),
    (
        "ensure_branch",
        "Create or checkout branch (normally pre-set by harness)",
        {"branch": {"type": "string"}, "start_from": {"type": "string", "default": "HEAD"}},
        ["branch"],
    ),
    (
        "commit_all",
        "Stage everything and git commit",
        {"message": {"type": "string"}},
        ["message"],
    ),
    (
        "git_push",
        "Git push branch to origin",
        {"branch": {"type": "string"}, "force": {"type": "boolean", "default": False}},
        ["branch"],
    ),
    (
        "open_draft_pr",
        "Open a draft pull request via GitHub API",
        {
            "head": {"type": "string", "description": "Head branch name (same fork)"},
            "title": {"type": "string"},
            "body": {"type": "string"},
        },
        ["head", "title", "body"],
    ),
    (
        "create_gist",
        "Create a single-file gist for long blobs",
        {
            "description": {"type": "string"},
            "filename": {"type": "string"},
            "content": {"type": "string"},
            "public": {"type": "boolean", "default": False},
        },
        ["description", "filename", "content"],
    ),
]


def tools_anthropic_specs() -> list[dict[str, Any]]:
    """Return ``tools=[]`` payloads for the Anthropic Messages API."""
    return [_anthropic_tool_spec(name, desc, props, req) for name, desc, props, req in _TOOL_DEFS]


def _anthropic_tool_spec(
    name: str,
    description: str,
    props: dict[str, dict[str, Any]],
    required: list[str],
) -> dict[str, Any]:
    props_out = {k: {key: val for key, val in v.items() if key != "default"} for k, v in props.items()}
    schema: dict[str, Any] = {"type": "object", "properties": props_out}
    if required:
        schema["required"] = required
    return {"name": name, "description": description, "input_schema": schema}


def tools_openai_specs() -> list[dict[str, Any]]:
    """Return ``tools=[]`` payloads for Chat Completions."""
    return [tool_spec(name, desc, props, req) for name, desc, props, req in _TOOL_DEFS]


def tool_spec(
    name: str,
    description: str,
    props: dict[str, dict[str, Any]],
    required: list[str],
) -> dict[str, Any]:
    props_out: dict[str, Any] = {}
    for k, v in props.items():
        d = {key: val for key, val in v.items() if key != "default"}
        props_out[k] = d

    schema: dict[str, Any] = {
        "type": "object",
        "properties": props_out,
    }

    if required:
        schema["required"] = required

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": schema,
        },
    }


def dispatch_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a parsed tool invocation; return plaintext for the assistant."""

    if name == "read_file":
        return fs.read_file(str(arguments["path"]))

    if name == "write_file":
        return fs.write_file(str(arguments["path"]), str(arguments["content"]))

    if name == "search":
        return fs.search(str(arguments["pattern"]), str(arguments.get("subdir") or "."))

    if name == "run_shell":
        return shell.run_shell(
            str(arguments["command"]),
            timeout_s=int(arguments.get("timeout_seconds") or 120),
        )

    if name == "run_tests":
        return tests.run_tests(
            str(arguments.get("target") or ""),
            verbose=bool(arguments.get("verbose")),
        )

    if name == "git_status":
        return git_ops.git_status_summary()

    if name == "git_diff_stat":
        return git_ops.git_diff_stat()

    if name == "ensure_branch":
        return git_ops.ensure_branch(
            str(arguments["branch"]), str(arguments.get("start_from") or "HEAD")
        )

    if name == "commit_all":
        return git_ops.commit_all(str(arguments["message"]))

    if name == "git_push":
        return git_ops.push_upstream(str(arguments["branch"]), force=bool(arguments.get("force")))

    if name == "open_draft_pr":
        try:
            return ghapi.create_draft_pr(
                str(arguments["head"]),
                str(arguments["title"]),
                str(arguments["body"]),
            )

        except Exception as exc:  # noqa: BLE001
            return f"open_draft_pr error: {exc}"

    if name == "create_gist":
        try:
            return ghapi.create_gist(
                description=str(arguments.get("description") or ""),
                filename=str(arguments.get("filename") or "scratch.txt"),
                content=str(arguments.get("content") or ""),
                public=bool(arguments.get("public")),
            )
        except Exception as exc:  # noqa: BLE001
            return f"create_gist error: {exc}"

    return f"unknown tool: {name}"
