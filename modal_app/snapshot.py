"""Periodic filesystem snapshot refresh for faster sandbox cold starts."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import modal

from modal_app.sandbox import REPO_IMAGE, SANDBOX_SECRETS, SNAPSHOT_META
from modal_app.state import modal_app

log = logging.getLogger(__name__)


@modal_app.function(
    schedule=modal.Cron("*/30 * * * *"),
    timeout=1200,
    secrets=[modal.Secret.from_name("github-token")],
)
def refresh_snapshot() -> None:
    sb = modal.Sandbox.create(
        "sleep",
        "infinity",
        image=REPO_IMAGE,
        app=modal_app,
        cpu=2.0,
        memory=4096,
        timeout=1100,
        secrets=SANDBOX_SECRETS,
    )
    try:
        proc = sb.exec(
            "bash",
            "-lc",
            "cd /app && git pull --ff-only && "
            "(pip install -e '.[dev]' || pip install -e . || pip install .) || true",
        )
        proc.wait()
        if proc.returncode != 0:
            err = "".join(
                line if isinstance(line, str) else str(line) for line in proc.stderr
            )[:400]
            log.warning("snapshot_update_nonzero code=%s stderr=%s", proc.returncode, err)

        new_image = sb.snapshot_filesystem()
        SNAPSHOT_META["image_id"] = new_image.object_id
        SNAPSHOT_META["snapshot_built_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        log.info("snapshot_refreshed image_id=%s", new_image.object_id)
    finally:
        sb.terminate(wait=True)


__all__ = ["refresh_snapshot"]
