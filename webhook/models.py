"""Pydantic models for Linq webhook payloads."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


class LinqMediaItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url: str
    type: str | None = None


class LinqMessageData(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    from_: str = Field(default="", alias="from")
    to: str | None = None
    protocol: str | None = None
    text: str | None = None
    timestamp: datetime | str | None = None
    media: list[LinqMediaItem] | None = None
    reaction: str | None = None
    reply_to_message_id: str | None = Field(default=None, alias="replyToMessageId")


class LinqWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event: str
    data: LinqMessageData | None = None
