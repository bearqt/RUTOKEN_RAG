from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceDocument:
    document_id: str
    page_id: str
    source_url: str
    title: str
    author: str | None
    last_modified: str | None
    raw_markdown: str
    clean_markdown: str


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    document_id: str
    page_id: str
    source_url: str
    title: str
    heading_path: list[str]
    text: str
    chunk_type: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class QueryAnalysis:
    original_query: str
    rewritten_query: str
    filters: dict[str, list[str] | str]
    intent: str
    needs_code: bool


@dataclass(slots=True)
class RetrievedChunk:
    chunk: Chunk
    dense_score: float = 0.0
    sparse_score: float = 0.0
    fused_score: float = 0.0
    rerank_score: float = 0.0


@dataclass(slots=True)
class Citation:
    source_url: str
    title: str
    heading_path: list[str]
    chunk_id: str


@dataclass(slots=True)
class PipelineResult:
    analysis: QueryAnalysis
    answer: str
    citations: list[Citation]
    retrieved_chunks: list[RetrievedChunk]
