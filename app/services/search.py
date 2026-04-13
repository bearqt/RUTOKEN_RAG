from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.domain.models import Chunk, RetrievedChunk, SearchResult
from app.providers.gigachat import GigaChatEmbeddingsProvider
from app.providers.reranker import Reranker
from app.retrieval.bm25_index import BM25Index
from app.retrieval.qdrant_store import QdrantStore
from app.services.enrichment import metadata_matches
from app.services.graph_search import GraphSearchService
from app.services.ner import extract_named_entities
from app.services.storage import load_chunks

RETRIEVAL_MODE_VALUES = {"dense", "bm25", "graph", "hybrid"}


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
        self._graph = GraphSearchService(settings)
        self._artifacts = self._load_artifacts()

    def refresh(self) -> None:
        self._artifacts = self._load_artifacts()
        self._graph.refresh()

    def search(
        self,
        rewritten_query: str,
        filters: dict[str, list[str] | str],
        query_entities: dict[str, list[str]] | None = None,
        query_mode: str = "classic",
        retrieval_mode: str = "hybrid",
    ) -> SearchResult:
        retrieval_mode = normalize_retrieval_mode(retrieval_mode)
        if not self._artifacts.chunks_by_id:
            return SearchResult(chunks=[], ranked_chunks=[], retrieval_mode=retrieval_mode, graph_facts=[])

        query_entities = query_entities or extract_named_entities(rewritten_query)
        pkcs11_reference_mode = _is_pkcs11_reference_query(rewritten_query, query_entities)
        effective_graph_query_mode = _effective_graph_query_mode(query_mode, retrieval_mode)

        dense_hits: list[tuple[str, float]] = []
        sparse_hits = []
        graph_result = self._graph.search(
            query_entities,
            effective_graph_query_mode,
            self._settings.graph_candidate_count,
        ) if retrieval_mode in {"graph", "hybrid"} else self._graph.search({}, "classic", 0)

        if retrieval_mode in {"dense", "hybrid"}:
            dense_vector = self._embeddings.embed_query(rewritten_query)
            dense_hits = self._qdrant.search(dense_vector, self._settings.dense_candidate_count, filters)

        if retrieval_mode in {"bm25", "hybrid"}:
            sparse_hits = self._artifacts.bm25.search(rewritten_query, self._settings.sparse_candidate_count, filters)

        retrieved: dict[str, RetrievedChunk] = {}
        for rank, (chunk_id, score) in enumerate(dense_hits, start=1):
            chunk = self._artifacts.chunks_by_id.get(chunk_id)
            if chunk is None:
                continue
            retrieved.setdefault(chunk_id, RetrievedChunk(chunk=chunk))
            retrieved[chunk_id].dense_score = score
            retrieved[chunk_id].fused_score += _dense_rank_score(rank, pkcs11_reference_mode, query_mode)

        for rank, hit in enumerate(sparse_hits, start=1):
            chunk = self._artifacts.chunks_by_id.get(hit.chunk_id)
            if chunk is None:
                continue
            retrieved.setdefault(hit.chunk_id, RetrievedChunk(chunk=chunk))
            retrieved[hit.chunk_id].sparse_score = hit.score
            retrieved[hit.chunk_id].fused_score += _sparse_rank_score(rank, pkcs11_reference_mode, query_mode)

        for rank, hit in enumerate(graph_result.hits, start=1):
            chunk = self._artifacts.chunks_by_id.get(hit.chunk_id)
            if chunk is None:
                continue
            retrieved.setdefault(hit.chunk_id, RetrievedChunk(chunk=chunk))
            retrieved[hit.chunk_id].graph_score = hit.score
            retrieved[hit.chunk_id].fused_score += _graph_rank_score(rank, effective_graph_query_mode)
            retrieved[hit.chunk_id].fused_score += hit.score * self._settings.graph_fusion_weight

        if retrieval_mode == "hybrid":
            for item in retrieved.values():
                item.fused_score += _entity_overlap_boost(item.chunk.metadata, query_entities)
                if pkcs11_reference_mode:
                    item.fused_score += _pkcs11_reference_boost(item.chunk, query_entities, rewritten_query)

        candidates = sorted(retrieved.values(), key=lambda item: item.fused_score, reverse=True)
        candidates = [
            item
            for item in candidates
            if not filters or metadata_matches(item.chunk.metadata, filters)
        ][: self._settings.rerank_candidate_count]

        rerank_scores = self._reranker.rerank(rewritten_query, [item.chunk.text for item in candidates])
        for item, score in zip(candidates, rerank_scores, strict=False):
            item.rerank_score = score

        ranked_chunks = sorted(candidates, key=lambda item: item.rerank_score, reverse=True)
        return SearchResult(
            chunks=ranked_chunks[: self._settings.final_context_count],
            ranked_chunks=ranked_chunks,
            retrieval_mode=retrieval_mode,
            graph_facts=graph_result.facts,
        )

    def _load_artifacts(self) -> SearchArtifacts:
        chunks = load_chunks(self._settings.chunks_path)
        chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        bm25 = BM25Index.load(self._settings.bm25_path, chunks)
        return SearchArtifacts(chunks_by_id=chunks_by_id, bm25=bm25)


def normalize_retrieval_mode(value: str | None) -> str:
    normalized = (value or "hybrid").strip().lower()
    if normalized in RETRIEVAL_MODE_VALUES:
        return normalized
    return "hybrid"


def _effective_graph_query_mode(query_mode: str, retrieval_mode: str) -> str:
    if retrieval_mode == "graph":
        return "graph_first"
    return query_mode


def _entity_overlap_boost(metadata: dict, query_entities: dict[str, list[str]]) -> float:
    weights = {
        "api_symbols": 0.35,
        "components": 0.14,
        "products": 0.1,
        "interfaces": 0.08,
        "os_tags": 0.05,
        "language_tags": 0.05,
    }
    boost = 0.0
    for key, weight in weights.items():
        expected = set(query_entities.get(key, []))
        if not expected:
            continue
        actual = set(metadata.get(key, []))
        if not actual:
            continue
        overlap = expected.intersection(actual)
        if overlap:
            boost += min(len(overlap), 3) * weight
    return boost


def _is_pkcs11_reference_query(rewritten_query: str, query_entities: dict[str, list[str]]) -> bool:
    if "pkcs11" not in query_entities.get("interfaces", []):
        return False
    query_lower = rewritten_query.lower()
    markers = (
        "функц",
        "вызов",
        "синтаксис",
        "параметр",
        "назначение",
        "примечание",
        "возвращаем",
        "пример",
        "объект",
        "подпис",
        "проверк",
        "ключ",
        "reference",
    )
    return any(marker in query_lower for marker in markers)


def _dense_rank_score(rank: int, pkcs11_reference_mode: bool, query_mode: str) -> float:
    if pkcs11_reference_mode:
        return 0.6 / (75 + rank)
    if query_mode == "graph_first":
        return 0.8 / (65 + rank)
    return 1.0 / (60 + rank)


def _sparse_rank_score(rank: int, pkcs11_reference_mode: bool, query_mode: str) -> float:
    if pkcs11_reference_mode:
        return 2.0 / (35 + rank)
    if query_mode == "graph_first":
        return 0.9 / (55 + rank)
    if query_mode == "mixed":
        return 1.1 / (55 + rank)
    return 1.0 / (60 + rank)


def _graph_rank_score(rank: int, query_mode: str) -> float:
    if query_mode == "graph_first":
        return 1.6 / (30 + rank)
    if query_mode == "mixed":
        return 1.1 / (40 + rank)
    return 0.0


def _pkcs11_reference_boost(chunk: Chunk, query_entities: dict[str, list[str]], rewritten_query: str) -> float:
    boost = 0.0
    if chunk.chunk_type == "reference":
        boost += 0.35

    title_lower = chunk.title.lower()
    heading_text = " ".join(chunk.heading_path)
    heading_lower = heading_text.lower()
    query_lower = rewritten_query.lower()

    if title_lower.startswith("функции "):
        boost += 0.08

    expected_symbols = query_entities.get("api_symbols", [])
    if expected_symbols:
        for symbol in expected_symbols:
            if symbol.lower() in heading_lower:
                boost += 0.35
            elif symbol in chunk.text:
                boost += 0.2

    if any(term in query_lower for term in ("какие разделы", "описание функции", "какие секции")):
        section_terms = ("синтаксис", "параметры", "назначение", "примечание", "возвращаемые значения", "пример")
        present = sum(1 for term in section_terms if term in chunk.text.lower())
        boost += min(present, 6) * 0.03

    return boost
