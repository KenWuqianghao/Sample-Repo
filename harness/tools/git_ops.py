"""Git primitives (workspace-local)."""

from __future__ import annotations

import subprocess

from harness.state import workspace_root


def _run(git_args: list[str]) -> tuple[int, str]:
    root = str(workspace_root())
    proc = subprocess.run(
        ["git", "-C", root, *git_args],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    out = proc.stdout.strip()
    err = proc.stderr.strip()
    if err:
        out = (out + "\n" + err).strip()
    return proc.returncode, out or "(no output)"


def git_status_summary() -> str:
    _, o = _run(["status", "--porcelain=v1"])
    return o[:8000]


def git_diff_stat() -> str:
    _, o = _run(["diff", "--stat", "HEAD"])
    return o[:8000]


def ensure_branch(branch: str, start_from: str = "HEAD") -> str:
    _, fetch_out = _run(["fetch", "origin"])
    msg_parts: list[str] = []
    if fetch_out and fetch_out != "(no output)":
        msg_parts.append(fetch_out[:600])

    rc_local, _ = _run(["rev-parse", "--verify", branch])
    if rc_local == 0:
        _, co = _run(["checkout", branch])
        msg_parts.append(co)
        return "\n".join(msg_parts)

    rc_remote, _ = _run(["rev-parse", "--verify", f"origin/{branch}"])
    if rc_remote == 0:
        _, co = _run(["checkout", "--track", f"origin/{branch}"])
        msg_parts.append(co)
        return "\n".join(msg_parts)

    _, nb = _run(["checkout", "-b", branch, start_from])
    msg_parts.append(nb)
    return "\n".join(msg_parts)


def commit_all(message: str) -> str:
    add_code, add_out = _run(["add", "-A"])
    if add_code != 0:
        return f"git add failed (exit={add_code}): {add_out}"
    code, co = _run(["commit", "-m", message])
    if code != 0 and "nothing to commit" in co.lower():
        return "nothing to commit"
    return f"exit={code}\n{co}"


def push_upstream(branch: str, *, force: bool = False) -> str:
    if force:
        return "forced push refused by policy"
    code, txt = _run(["push", "-u", "origin", branch])
    prefix = "" if code == 0 else f"exit={code}\n"
    merged = prefix + txt
    return merged[:8000]
