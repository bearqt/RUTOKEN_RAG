from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=3)


class CitationResponse(BaseModel):
    source_url: str
    title: str
    heading_path: list[str]
    chunk_id: str


class RetrievedChunkResponse(BaseModel):
    chunk_id: str
    title: str
    heading_path: list[str]
    source_url: str
    chunk_type: str
    dense_score: float
    sparse_score: float
    fused_score: float
    rerank_score: float
    text: str


class QueryResponse(BaseModel):
    original_query: str
    rewritten_query: str
    filters: dict
    answer: str
    citations: list[CitationResponse]
    retrieved_chunks: list[RetrievedChunkResponse]


class IngestResponse(BaseModel):
    documents: int
    chunks: int
    vector_size: int


class HealthResponse(BaseModel):
    status: str
    chunks_indexed: bool
    manifest_exists: bool
    openrouter_configured: bool
    gigachat_configured: bool

