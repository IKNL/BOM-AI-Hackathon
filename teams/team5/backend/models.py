"""Pydantic data models for the cancer-info-chat system."""

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, model_validator


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str
    profile: Literal["patient", "professional", "policymaker"]
    history: list[ChatMessage] = []


class Citation(BaseModel):
    url: str
    title: str
    reliability: str


class SourceCard(BaseModel):
    source: str
    url: str
    reliability: str
    contributed: bool


class ChartData(BaseModel):
    type: Literal["line", "bar", "value"]
    title: str
    data: list[dict]
    x_key: str
    y_key: str
    unit: Optional[str] = None


class FeedbackEntry(BaseModel):
    session_id: str
    message_id: str
    rating: Literal["positive", "negative"]
    comment: Optional[str] = None
    query: str
    sources_tried: list[str]
    profile: Optional[str] = None
    timestamp: Optional[datetime] = None

    @model_validator(mode="after")
    def set_timestamp(self) -> "FeedbackEntry":
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        return self


class SourceResult(BaseModel):
    data: dict | list | str | None
    summary: str
    sources: list[Citation]
    visualizable: bool


class SessionContext(BaseModel):
    session_id: str
    profile: Literal["patient", "professional", "policymaker"]
    history: list[ChatMessage]
    inferred_intent: Optional[str] = None
