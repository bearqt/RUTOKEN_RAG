from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

RetrievalMode = Literal["dense", "bm25", "graph", "hybrid"]


class QueryRequest(BaseModel):
    question: str = Field(min_length=3)
    retrieval_mode: RetrievalMode = "hybrid"


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
    graph_score: float
    fused_score: float
    rerank_score: float
    text: str


class QueryResponse(BaseModel):
    original_query: str
    rewritten_query: str
    filters: dict
    query_mode: str
    retrieval_mode: RetrievalMode
    routing_confidence: float | None = None
    routing_reason: str | None = None
    answer: str
    graph_facts: list[str]
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


class BenchmarkQuestionInput(BaseModel):
    id: str | None = None
    case_key: str = Field(min_length=1)
    question: str = Field(min_length=3)
    tags: list[str] = Field(default_factory=list)
    reference_answer: str | None = None
    exact_answer: str | None = None
    required_terms: list[str] = Field(default_factory=list)
    required_any: list[list[str]] = Field(default_factory=list)
    forbidden_terms: list[str] = Field(default_factory=list)
    required_sources: list[str] = Field(default_factory=list)
    expected_refusal: bool = False
    notes: str | None = None


class BenchmarkQuestionSetInput(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    questions: list[BenchmarkQuestionInput] = Field(default_factory=list)


class BenchmarkQuestionSetSummaryResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    question_count: int
    last_run_at: datetime | None = None


class BenchmarkQuestionSetResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    questions: list[dict[str, Any]]


class BenchmarkRunSummaryResponse(BaseModel):
    id: str
    set_id: str
    set_name: str
    retrieval_mode: RetrievalMode | None = None
    created_at: datetime
    total_cases: int
    passed_cases: int
    pass_rate: float
    average_score: float
    average_latency_ms: float
    p95_latency_ms: float
