from __future__ import annotations

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.config import Settings
from app.domain.models import Citation, Chunk, PipelineResult, QueryAnalysis, RetrievedChunk, SourceDocument
from app.services.parsing import load_source_documents
from app.services.text_utils import clean_inline_markdown, tokenize_for_bm25


@dataclass(slots=True)
class DocumentHit:
    document_id: str
    score: float


class BM25BaselineService:
    """Simple lexical baseline over full documents.

    This baseline intentionally avoids the RAG chunking/enrichment pipeline:
    - one indexed unit = one source document
    - no overlap
    - no metadata enrichment
    - search text = document title + full document text
    """

    def __init__(self, settings: Settings, top_k: int | None = None) -> None:
        self._settings = settings
        self._top_k = top_k or settings.final_context_count
        self._documents_by_id: dict[str, SourceDocument] = {}
        self._document_ids: list[str] = []
        self._index: BM25Okapi | None = None
        self.refresh()

    def refresh(self) -> None:
        documents = load_source_documents(self._settings.scrape_dir)
        self._documents_by_id = {document.document_id: document for document in documents}
        self._document_ids = [document.document_id for document in documents]
        tokenized_documents = [self._document_tokens(document) for document in documents]
        self._index = BM25Okapi(tokenized_documents) if tokenized_documents else None

    def run(self, question: str, retrieval_mode: str = "bm25_baseline") -> PipelineResult:
        hits = self._search(question)
        retrieved_documents = [self._to_retrieved_chunk(hit) for hit in hits]

        citations = [
            Citation(
                source_url=item.chunk.source_url,
                title=item.chunk.title,
                heading_path=item.chunk.heading_path,
                chunk_id=item.chunk.chunk_id,
            )
            for item in retrieved_documents
        ]

        return PipelineResult(
            analysis=QueryAnalysis(
                original_query=question,
                rewritten_query=question,
                filters={},
                intent="keyword_search",
                needs_code=False,
                entities={},
                query_mode="classic",
                routing_confidence=1.0,
                routing_reason="bm25_baseline_document_index_no_llm",
            ),
            answer=_build_answer(question, retrieved_documents),
            citations=citations,
            retrieved_chunks=retrieved_documents,
            ranked_chunks=retrieved_documents,
            retrieval_mode=retrieval_mode,
            graph_facts=[],
        )

    def _search(self, query: str) -> list[DocumentHit]:
        if self._index is None:
            return []

        query_tokens = tokenize_for_bm25(query)
        scores = self._index.get_scores(query_tokens)
        ranked_hits = sorted(
            (
                DocumentHit(document_id=self._document_ids[index], score=float(score))
                for index, score in enumerate(scores)
                if score > 0
            ),
            key=lambda item: item.score,
            reverse=True,
        )
        return ranked_hits[: self._top_k]

    def _to_retrieved_chunk(self, hit: DocumentHit) -> RetrievedChunk:
        document = self._documents_by_id[hit.document_id]
        return RetrievedChunk(
            chunk=Chunk(
                chunk_id=document.document_id,
                document_id=document.document_id,
                page_id=document.page_id,
                source_url=document.source_url,
                title=document.title,
                heading_path=[],
                text=document.clean_markdown,
                chunk_type="document",
                metadata={},
            ),
            sparse_score=hit.score,
            fused_score=hit.score,
            rerank_score=hit.score,
        )

    @staticmethod
    def _document_tokens(document: SourceDocument) -> list[str]:
        search_text = f"{clean_inline_markdown(document.title)}\n\n{document.clean_markdown}"
        return tokenize_for_bm25(search_text)


def _build_answer(question: str, documents: list[RetrievedChunk]) -> str:
    if not documents:
        return (
            "Релевантные документы не найдены. "
            "BM25 baseline не использует LLM и возвращает только найденные текстовые совпадения."
        )

    lines = [
        f"Запрос: {question}",
        "Режим: BM25 baseline без LLM",
        "Единица поиска: целый документ",
        "",
        "Найденные документы:",
        "",
    ]
    for index, item in enumerate(documents, start=1):
        lines.extend(
            [
                f"{index}. {item.chunk.title}",
                _extract_snippet(item.chunk.text, question),
                f"Источник: {item.chunk.source_url}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def _extract_snippet(text: str, query: str, window: int = 420) -> str:
    cleaned = clean_inline_markdown(text)
    if not cleaned:
        return ""

    query_tokens = [token for token in tokenize_for_bm25(query) if len(token) > 2]
    lowered = cleaned.lower()
    best_position = -1
    for token in query_tokens:
        position = lowered.find(token)
        if position != -1 and (best_position == -1 or position < best_position):
            best_position = position

    if best_position == -1:
        sentences = re.split(r"(?<=[.!?])\s+|\n+", cleaned)
        fallback = " ".join(sentence.strip() for sentence in sentences[:3] if sentence.strip())
        return fallback[:window].strip()

    start = max(best_position - window // 3, 0)
    end = min(start + window, len(cleaned))
    snippet = cleaned[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(cleaned):
        snippet = snippet + "..."
    return snippet
