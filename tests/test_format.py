"""Formatting helpers."""

from __future__ import annotations

from harness.format import pick_deliverable, split_for_imessage


def test_split_under_cap_single() -> None:
    parts = split_for_imessage("hello", max_len=800)

    assert parts == ["hello"]


def test_split_long_has_chunk_markers() -> None:
    blob = "a" * 850

    parts = split_for_imessage(blob, max_len=800)

    assert len(parts) >= 2

    assert " (1/" in parts[0]


def test_pick_deliverable_pr_when_multi_file() -> None:
    kind = pick_deliverable(
        changed_files=2,
        insertion_plus_deletion=10,
        response_text_len=80,
        has_repo=True,
    )

    assert kind == "pr"
