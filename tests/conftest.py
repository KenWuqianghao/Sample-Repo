"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def harness_writable_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Local machines rarely have a writable ``/app``; Modal sandboxes use ``/app``."""
    monkeypatch.setenv("HARNESS_WORKDIR", str(tmp_path))
