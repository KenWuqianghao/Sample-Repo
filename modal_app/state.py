"""Modal App object (minimal module to avoid import cycles)."""

from __future__ import annotations

import modal

# Default image for every function (web + workers). Custom images do not get the deploy
# CLI's PythonPackage mount unless sources are added here.
RUNTIME_IMAGE = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "modal>=0.73",
        "fastapi>=0.115",
        "uvicorn[standard]>=0.29",
        "httpx>=0.27",
        "pydantic>=2.7",
        "python-dotenv>=1.0",
        "structlog>=24.0",
    )
    .add_local_python_source("modal_app", "webhook", "linq", "harness")
)

modal_app = modal.App(
    "imessage-coding-agent",
    image=RUNTIME_IMAGE,
    secrets=[
        modal.Secret.from_name("linq-secrets"),
        modal.Secret.from_name("model-secrets"),
        modal.Secret.from_name("github-token"),
    ],
)
