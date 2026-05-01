"""CLI entry: ``python -m harness.run`` inside the Modal sandbox (or locally for tests)."""

from __future__ import annotations

import argparse
import json
import sys

from harness.agent import run as agent_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Coding harness (one turn)")
    parser.add_argument("--prompt", default=None, help="Inline prompt (use file for large prompts)")
    parser.add_argument(
        "--prompt-file",
        default=None,
        help="Path to UTF-8 file with the prompt (preferred from agent)",
    )
    parser.add_argument(
        "--output-format",
        choices=("json", "text"),
        default="json",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="No progress JSON lines on stdout"
    )
    parser.add_argument(
        "--media-url",
        action="append",
        default=[],
        dest="media_urls",
        help="Attachment URL (repeatable); appended to the user message",
    )
    args = parser.parse_args()

    if args.prompt_file:
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
    elif args.prompt is not None:
        prompt = args.prompt
    else:
        parser.error("Provide --prompt or --prompt-file")

    result = agent_run(
        prompt,
        emit_progress=not args.quiet,
        emit_final_json_line=False,
        media_urls=args.media_urls or None,
    )
    if args.output_format == "json":
        print(json.dumps({"result": result}, ensure_ascii=False))
    else:
        print(result, end="" if result.endswith("\n") else "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": str(e), "type": type(e).__name__}), file=sys.stderr)
        sys.exit(1)
