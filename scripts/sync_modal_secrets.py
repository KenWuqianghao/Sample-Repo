#!/usr/bin/env python3
"""Push split slices of .env to Modal secrets (linq-secrets, model-secrets, github-token).

Skips keys that must not go to the cloud (Modal CLI tokens). Omits empty values.
Requires: pip install python-dotenv; Modal CLI authenticated (e.g. ~/.modal.toml).

Usage:
  .venv/bin/python scripts/sync_modal_secrets.py
  .venv/bin/python scripts/sync_modal_secrets.py /path/to/.env
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from dotenv import dotenv_values
except ImportError as e:
    raise SystemExit("Install python-dotenv: pip install python-dotenv") from e

SKIP_KEYS = frozenset({"MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET"})

LINQ_KEYS = frozenset({"LINQ_TOKEN", "LINQ_SECRET", "LINQ_FROM_NUMBER", "ALLOWED_SENDERS"})
GITHUB_KEYS = frozenset({"GITHUB_TOKEN", "GH_TOKEN", "GITHUB_ACCESS_TOKEN", "REPO_URL"})


def _load_env(path: Path) -> dict[str, str]:
    raw = dotenv_values(path)
    out: dict[str, str] = {}
    for k, v in raw.items():
        if not k or k in SKIP_KEYS:
            continue
        if v is None or str(v).strip() == "":
            continue
        out[k] = str(v)
    return out


def _write_dotenv(path: Path, data: dict[str, str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for key in sorted(data):
            val = data[key].replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
            f.write(f'{key}="{val}"\n')


def _modal_cmd(root: Path) -> list[str]:
    exe = root / ".venv" / "bin" / "modal"
    if exe.is_file():
        return [str(exe), "secret", "create"]
    return ["modal", "secret", "create"]


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    env_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / ".env"
    if not env_path.is_file():
        print(f"Missing file: {env_path}", file=sys.stderr)
        return 1

    full = _load_env(env_path)
    linq = {k: full[k] for k in LINQ_KEYS if k in full}
    github = {k: full[k] for k in GITHUB_KEYS if k in full}
    model = {
        k: v
        for k, v in full.items()
        if k not in LINQ_KEYS and k not in GITHUB_KEYS and k not in SKIP_KEYS
    }

    specs = [
        ("linq-secrets", linq),
        ("github-token", github),
        ("model-secrets", model),
    ]

    base = _modal_cmd(root)
    with tempfile.TemporaryDirectory(prefix="modal-secrets-") as tmp:
        tdir = Path(tmp)
        for name, data in specs:
            if not data:
                print(f"skip {name}: no keys in {env_path.name} (not overwriting)", file=sys.stderr)
                continue
            f = tdir / f"{name}.env"
            _write_dotenv(f, data)
            cmd = [*base, name, "--from-dotenv", str(f), "--force"]
            print("+", " ".join(cmd))
            subprocess.run(cmd, check=True, cwd=str(root))
    print("ok: Modal secrets updated from --force")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
