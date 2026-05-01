"""Pydantic models for Linq Partner API request/response helpers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Protocol = Literal["imessage", "rcs", "sms"]


class SendMessageRequest(BaseModel):
    """POST /messages body."""

    model_config = {"populate_by_name": True}

    from_: str = Field(alias="from")
    to: str
    text: str
    protocol: Protocol = "imessage"
    reply_to_message_id: str | None = Field(default=None, alias="replyToMessageId")


class SendTypingRequest(BaseModel):
    """POST /typing body."""

    to: str
    active: bool


class SendReactionRequest(BaseModel):
    """POST /messages/{message_id}/reactions body."""

    reaction: str
