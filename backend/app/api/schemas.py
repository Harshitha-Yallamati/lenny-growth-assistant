import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    error: str
    detail: str


class SessionCreateRequest(BaseModel):
    user_metadata: dict = Field(default_factory=dict)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    provider: str | None
    model: str | None
    skill: str | None
    citations: list[dict] | None
    artifact: dict | None
    grounded: bool | None
    created_at: datetime


class SessionDetailResponse(SessionResponse):
    messages: list[MessageResponse]


class ChatRequest(BaseModel):
    session_id: uuid.UUID
    message: str = Field(min_length=1, max_length=8000)
    skill: Literal["qa", "ship30", "artifact"] | None = None
    artifact_format: Literal["markdown", "html"] | None = None


class ChatResponse(BaseModel):
    message: MessageResponse
    fell_back_to_ollama: bool


class ConfigResponse(BaseModel):
    active_provider: str
    configured_default: str
    provider_status: dict[str, bool]
    ollama_model: str
    anthropic_model: str
    openai_model: str


class ConfigUpdateRequest(BaseModel):
    provider: Literal["ollama", "anthropic", "openai"]


class SourceExcerpt(BaseModel):
    chunk_index: int
    content: str


class SourceDetailResponse(BaseModel):
    title: str
    url: str | None
    total_chunks: int
    excerpts: list[SourceExcerpt]
