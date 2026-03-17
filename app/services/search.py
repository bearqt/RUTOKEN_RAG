from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.domain.models import Chunk, RetrievedChunk
from app.providers.gigachat import GigaChatEmbeddingsProvider
from app.providers.reranker import Reranker
from app.retrieval.bm25_index import BM25Index
from app.retrieval.qdrant_store import QdrantStore
from app.services.enrichment import metadata_matches
from app.services.storage import load_chunks


@dataclass(slots=True)
class SearchArtifacts:
    chunks_by_id: dict[str, Chunk]
    bm25: BM25Index


class HybridSearchService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._embeddings = GigaChatEmbeddingsProvider(settings)
        self._qdrant = QdrantStore(settings)
        self._reranker = Reranker(settings)
        self._artifacts = self._load_artifacts()

    def refresh(self) -> None:
        self._artifacts = self._load_artifacts()

    def search(self, rewritten_query: str, filters: dict[str, list[str] | str]) -> list[RetrievedChunk]:
        if not self._artifacts.chunks_by_id:
            return []

        dense_vector = self._embeddings.embed_query(rewritten_query)
        dense_hits = self._qdrant.search(dense_vector, self._settings.dense_candidate_count, filters)
        sparse_hits = self._artifacts.bm25.search(rewritten_query, self._settings.sparse_candidate_count, filters)

        retrieved: dict[str, RetrievedChunk] = {}
        for rank, (chunk_id, score) in enumerate(dense_hits, start=1):
            chunk = self._artifacts.chunks_by_id.get(chunk_id)
            if chunk is None:
                continue
            retrieved.setdefault(chunk_id, RetrievedChunk(chunk=chunk))
            retrieved[chunk_id].dense_score = score
            retrieved[chunk_id].fused_score += 1.0 / (60 + rank)

        for rank, hit in enumerate(sparse_hits, start=1):
            chunk = self._artifacts.chunks_by_id.get(hit.chunk_id)
            if chunk is None:
                continue
            retrieved.setdefault(hit.chunk_id, RetrievedChunk(chunk=chunk))
            retrieved[hit.chunk_id].sparse_score = hit.score
            retrieved[hit.chunk_id].fused_score += 1.0 / (60 + rank)

        candidates = sorted(retrieved.values(), key=lambda item: item.fused_score, reverse=True)
        candidates = [
            item
            for item in candidates
            if not filters or metadata_matches(item.chunk.metadata, filters)
        ][: self._settings.rerank_candidate_count]

        rerank_scores = self._reranker.rerank(rewritten_query, [item.chunk.text for item in candidates])
        for item, score in zip(candidates, rerank_scores, strict=False):
            item.rerank_score = score

        return sorted(candidates, key=lambda item: item.rerank_score, reverse=True)[: self._settings.final_context_count]

    def _load_artifacts(self) -> SearchArtifacts:
        chunks = load_chunks(self._settings.chunks_path)
        chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        bm25 = BM25Index.load(self._settings.bm25_path, chunks)
        return SearchArtifacts(chunks_by_id=chunks_by_id, bm25=bm25)

