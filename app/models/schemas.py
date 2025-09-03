from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkflowRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    user_id: str | None = None
    session_id: str | None = None


class Source(BaseModel):
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowMetadata(BaseModel):
    model: str
    latency_ms: float
    request_id: str | None
    retrieved_count: int
    mock_mode: bool


class WorkflowResponse(BaseModel):
    status: Literal["success"] = "success"
    result: str
    context_used: list[Source]
    metadata: WorkflowMetadata


class DocumentIn(BaseModel):
    text: str = Field(min_length=1, max_length=100_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    documents: list[DocumentIn] = Field(min_length=1, max_length=100)


class IngestResponse(BaseModel):
    status: Literal["success"] = "success"
    documents_received: int
    chunks_ingested: int
    chunk_ids: list[str]


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    # Populated for validation errors (422) with the offending fields; null otherwise.
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
