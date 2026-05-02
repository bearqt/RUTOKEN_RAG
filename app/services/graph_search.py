from __future__ import annotations

import math
from collections import defaultdict

from app.config import Settings
from app.domain.graph_models import GraphChunkHit, GraphNode, GraphSearchResult, GraphSnapshot
from app.providers.embeddings import OpenRouterEmbeddingsProvider, ProviderConfigurationError
from app.services.enrichment import metadata_matches
from app.services.graph_repository import GraphRepository
from app.services.graph_vector_store import GraphVectorStore
from app.services.text_utils import unique_preserve


QUERY_MODE_FACTORS = {
    "classic": 0.0,
    "mixed": 1.0,
    "graph_first": 1.25,
}

ENTITY_TYPE_WEIGHTS = {
    "api_symbols": 1.8,
    "components": 1.25,
    "interfaces": 1.0,
    "products": 1.0,
    "pkcs11_objects": 1.2,
    "pkcs11_mechanisms": 1.2,
    "error_codes": 1.1,
    "os_tags": 0.7,
    "language_tags": 0.5,
}

PREDICATE_PRIORS = {
    "supports_interface": 1.0,
    "available_on_os": 0.95,
    "uses_component": 1.0,
    "belongs_to_interface": 0.85,
    "returns_error_code": 0.9,
    "uses_pkcs11_object": 1.0,
    "uses_mechanism": 1.0,
    "compatible_with": 0.8,
}

RELATION_QUERY_MARKERS = (
    "supports",
    "requires",
    "compatible",
    "works on",
    "available on",
    "использ",
    "поддерж",
    "совмест",
    "требует",
    "доступен",
    "на какой ос",
    "на каких ос",
)


class GraphSearchService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._repository = GraphRepository(settings)
        self._repository.ensure_schema()
        self._vector_store = GraphVectorStore(settings)
        self._embeddings = OpenRouterEmbeddingsProvider(settings)
        self._snapshot = GraphSnapshot()
        self.refresh()

    def refresh(self) -> None:
        if not self._settings.graph_enabled:
            self._snapshot = GraphSnapshot()
            return
        self._snapshot = self._repository.load_graph()

    def search(
        self,
        query_entities: dict[str, list[str]],
        query_mode: str,
        top_k: int,
        query_text: str | None = None,
        filters: dict[str, list[str] | str] | None = None,
    ) -> GraphSearchResult:
        if not self._settings.graph_enabled or query_mode == "classic" or top_k <= 0:
            return GraphSearchResult()

        exact_nodes = self._seed_nodes(query_entities)
        semantic_entity_hits, semantic_relation_hits = self._semantic_hits(query_text, query_mode)
        if not exact_nodes and not semantic_entity_hits and not semantic_relation_hits:
            return GraphSearchResult()

        entity_scores: dict[str, float] = defaultdict(float)
        relation_scores: dict[tuple[str, str, str], float] = defaultdict(float)
        exact_entity_ids: set[str] = set()
        facts: list[str] = []
        mode_factor = QUERY_MODE_FACTORS.get(query_mode, 1.0)

        for node in exact_nodes:
            entity_type = str(node.metadata.get("entity_type") or "")
            score = self._entity_score(
                entity_type,
                self._settings.graph_exact_entity_weight,
                confidence=1.0,
                similarity=1.0,
                degree=self._snapshot.entity_degrees.get(node.node_id, 0),
            )
            entity_scores[node.node_id] += score
            exact_entity_ids.add(node.node_id)

        for hit in semantic_entity_hits:
            entity_id = str(hit.get("entity_id") or "")
            if entity_id not in self._snapshot.nodes_by_id:
                continue
            entity_type = str(hit.get("entity_type") or "")
            confidence = _safe_float(hit.get("confidence"), 1.0)
            similarity = _safe_float(hit.get("score"), 0.0)
            score = self._entity_score(
                entity_type,
                self._settings.graph_semantic_entity_weight,
                confidence=confidence,
                similarity=similarity,
                degree=self._snapshot.entity_degrees.get(entity_id, 0),
            )
            entity_scores[entity_id] += score

        ranked_seed_entities = sorted(entity_scores.items(), key=lambda item: item[1], reverse=True)
        for entity_id, base_score in ranked_seed_entities[: self._settings.graph_neighbor_limit]:
            facts.extend(self._expand_typed_neighbors(entity_id, base_score, mode_factor, entity_scores, relation_scores))
            self._expand_cooccurrence_neighbors(entity_id, base_score, mode_factor, entity_scores)

        for hit in semantic_relation_hits:
            src_id = str(hit.get("src_id") or "")
            tgt_id = str(hit.get("tgt_id") or "")
            predicate = str(hit.get("predicate") or "")
            relation_key = self._resolve_relation_key(src_id, tgt_id, predicate)
            if relation_key is None:
                continue
            similarity = _safe_float(hit.get("score"), 0.0)
            confidence = _safe_float(hit.get("confidence"), 1.0)
            score = self._relation_score(relation_key, similarity, confidence)
            relation_scores[relation_key] += score
            entity_scores[relation_key[0]] += score * 0.3
            entity_scores[relation_key[1]] += score * 0.3
            facts.append(self._format_relation(*relation_key))

        chunk_scores: dict[str, float] = defaultdict(float)
        chunk_entity_scores: dict[str, float] = defaultdict(float)
        chunk_relation_scores: dict[str, float] = defaultdict(float)
        chunk_feature_scores: dict[str, float] = defaultdict(float)
        chunk_exact_matches: dict[str, set[str]] = defaultdict(set)

        for entity_id, entity_score in entity_scores.items():
            for link in self._snapshot.entity_to_chunks.get(entity_id, []):
                if not self._chunk_allowed(link.chunk_id, filters):
                    continue
                contribution = entity_score * link.weight
                chunk_scores[link.chunk_id] += contribution
                chunk_entity_scores[link.chunk_id] += contribution
                if entity_id in exact_entity_ids:
                    chunk_exact_matches[link.chunk_id].add(entity_id)

        for relation_key, relation_score in relation_scores.items():
            for link in self._snapshot.relation_to_chunks.get(relation_key, []):
                if not self._chunk_allowed(link.chunk_id, filters):
                    continue
                contribution = relation_score * max(link.confidence, 0.2)
                chunk_scores[link.chunk_id] += contribution
                chunk_relation_scores[link.chunk_id] += contribution

        self._apply_chunk_feature_adjustments(
            chunk_scores,
            chunk_entity_scores,
            chunk_relation_scores,
            chunk_feature_scores,
            chunk_exact_matches,
            exact_entity_ids,
        )
        self._boost_neighbor_chunks(
            chunk_scores,
            chunk_entity_scores,
            chunk_relation_scores,
            chunk_feature_scores,
            filters,
        )

        ranked_hits = sorted(
            (
                GraphChunkHit(
                    chunk_id=chunk_id,
                    score=round(score, 4),
                    entity_score=round(chunk_entity_scores.get(chunk_id, 0.0), 4),
                    relation_score=round(chunk_relation_scores.get(chunk_id, 0.0), 4),
                    feature_score=round(chunk_feature_scores.get(chunk_id, 0.0), 4),
                )
                for chunk_id, score in chunk_scores.items()
                if score > 0
            ),
            key=lambda item: item.score,
            reverse=True,
        )[:top_k]

        return GraphSearchResult(
            hits=ranked_hits,
            facts=unique_preserve(facts)[: self._settings.graph_fact_limit],
        )

    def _semantic_hits(
        self,
        query_text: str | None,
        query_mode: str,
    ) -> tuple[list[dict], list[dict]]:
        if not query_text or not self._embeddings.is_configured():
            return [], []
        try:
            query_vector = self._embeddings.embed_query(query_text)
        except (ProviderConfigurationError, RuntimeError):
            return [], []

        entity_hits = self._vector_store.search_entities(query_vector, self._settings.graph_entity_top_k)
        relation_hits: list[dict] = []
        if query_mode in {"mixed", "graph_first"} or self._is_relation_heavy(query_text):
            relation_hits = self._vector_store.search_relations(query_vector, self._settings.graph_relation_top_k)
        return entity_hits, relation_hits

    def _seed_nodes(self, query_entities: dict[str, list[str]]) -> list[GraphNode]:
        seeds: list[GraphNode] = []
        for entity_type, values in query_entities.items():
            if entity_type not in ENTITY_TYPE_WEIGHTS:
                continue
            for value in values:
                node = self._snapshot.nodes_by_id.get(f"{entity_type}:{value}")
                if node is not None:
                    seeds.append(node)
        return seeds

    def _expand_typed_neighbors(
        self,
        entity_id: str,
        base_score: float,
        mode_factor: float,
        entity_scores: dict[str, float],
        relation_scores: dict[tuple[str, str, str], float],
    ) -> list[str]:
        facts: list[str] = []
        neighbors = sorted(
            self._snapshot.typed_entity_neighbors.get(entity_id, []),
            key=lambda item: item[1],
            reverse=True,
        )[: self._settings.graph_neighbor_limit]
        for neighbor_id, edge_weight, predicate in neighbors:
            neighbor_degree = self._snapshot.entity_degrees.get(neighbor_id, 0)
            propagated = (
                base_score
                * min(edge_weight, 1.0)
                * PREDICATE_PRIORS.get(predicate, 0.8)
                * 0.35
                * mode_factor
                / math.log(2 + neighbor_degree)
            )
            if propagated <= 0:
                continue
            entity_scores[neighbor_id] += propagated
            relation_key = self._resolve_relation_key(entity_id, neighbor_id, predicate)
            if relation_key is not None:
                relation_scores[relation_key] += propagated * 0.8
                facts.append(self._format_relation(*relation_key))
        return facts

    def _expand_cooccurrence_neighbors(
        self,
        entity_id: str,
        base_score: float,
        mode_factor: float,
        entity_scores: dict[str, float],
    ) -> None:
        neighbors = sorted(
            self._snapshot.entity_neighbors.get(entity_id, []),
            key=lambda item: item[1],
            reverse=True,
        )[: self._settings.graph_neighbor_limit]
        for neighbor_id, edge_weight, _ in neighbors:
            propagated = base_score * min(edge_weight, 1.0) * 0.08 * mode_factor
            if propagated <= 0:
                continue
            entity_scores[neighbor_id] += propagated

    def _apply_chunk_feature_adjustments(
        self,
        chunk_scores: dict[str, float],
        chunk_entity_scores: dict[str, float],
        chunk_relation_scores: dict[str, float],
        chunk_feature_scores: dict[str, float],
        chunk_exact_matches: dict[str, set[str]],
        exact_entity_ids: set[str],
    ) -> None:
        for chunk_id in list(chunk_scores):
            metadata = self._snapshot.chunk_metadata_by_id.get(chunk_id, {})
            feature_delta = 0.0
            if metadata.get("chunk_type") in {"reference", "table"}:
                feature_delta += self._settings.graph_reference_chunk_boost

            exact_hits = len(chunk_exact_matches.get(chunk_id, set()))
            if exact_hits > 1:
                feature_delta += min(exact_hits, 4) * 0.2

            hub_penalty = 0.0
            if exact_entity_ids:
                matched_degrees = [
                    self._snapshot.entity_degrees.get(entity_id, 0)
                    for entity_id in chunk_exact_matches.get(chunk_id, set())
                ]
                if matched_degrees:
                    hub_penalty = self._settings.graph_hub_penalty_alpha * math.log(2 + max(matched_degrees))

            chunk_scores[chunk_id] += feature_delta - hub_penalty
            chunk_feature_scores[chunk_id] += feature_delta - hub_penalty

    def _boost_neighbor_chunks(
        self,
        chunk_scores: dict[str, float],
        chunk_entity_scores: dict[str, float],
        chunk_relation_scores: dict[str, float],
        chunk_feature_scores: dict[str, float],
        filters: dict[str, list[str] | str] | None,
    ) -> None:
        top_chunks = sorted(chunk_scores.items(), key=lambda item: item[1], reverse=True)[: max(4, self._settings.graph_candidate_count)]
        for chunk_id, base_score in top_chunks:
            document_id = self._snapshot.chunk_to_document.get(chunk_id)
            if not document_id:
                continue
            ordered_chunks = self._snapshot.document_to_chunks.get(document_id, [])
            if chunk_id not in ordered_chunks:
                continue
            index = ordered_chunks.index(chunk_id)
            for neighbor_index in (index - 1, index + 1):
                if neighbor_index < 0 or neighbor_index >= len(ordered_chunks):
                    continue
                neighbor_id = ordered_chunks[neighbor_index]
                if not self._chunk_allowed(neighbor_id, filters):
                    continue
                boost = min(base_score, 1.5) * self._settings.graph_section_neighbor_boost
                if boost <= 0:
                    continue
                chunk_scores[neighbor_id] += boost
                chunk_feature_scores[neighbor_id] += boost

    def _chunk_allowed(
        self,
        chunk_id: str,
        filters: dict[str, list[str] | str] | None,
    ) -> bool:
        if not filters:
            return True
        metadata = self._snapshot.chunk_metadata_by_id.get(chunk_id, {})
        return metadata_matches(metadata, filters)

    def _entity_score(
        self,
        entity_type: str,
        base_weight: float,
        confidence: float,
        similarity: float,
        degree: int,
    ) -> float:
        return (
            base_weight
            * ENTITY_TYPE_WEIGHTS.get(entity_type, 0.8)
            * max(confidence, 0.1)
            * max(similarity, 0.1)
            / math.log(2 + degree)
        )

    def _relation_score(
        self,
        relation_key: tuple[str, str, str],
        similarity: float,
        confidence: float,
    ) -> float:
        src_degree = self._snapshot.entity_degrees.get(relation_key[0], 0)
        tgt_degree = self._snapshot.entity_degrees.get(relation_key[1], 0)
        return (
            self._settings.graph_relation_weight
            * max(similarity, 0.1)
            * max(confidence, 0.1)
            * PREDICATE_PRIORS.get(relation_key[2], 0.8)
            / math.log(2 + src_degree + tgt_degree)
        )

    def _resolve_relation_key(
        self,
        source_id: str,
        target_id: str,
        predicate: str,
    ) -> tuple[str, str, str] | None:
        direct_key = (source_id, target_id, predicate)
        if direct_key in self._snapshot.relation_to_chunks:
            return direct_key
        reverse_key = (target_id, source_id, predicate)
        if reverse_key in self._snapshot.relation_to_chunks:
            return reverse_key
        return None

    def _format_relation(self, source_id: str, target_id: str, predicate: str) -> str:
        source = self._snapshot.nodes_by_id.get(source_id)
        target = self._snapshot.nodes_by_id.get(target_id)
        if source is None or target is None:
            return f"{source_id} {predicate} {target_id}"
        return f"{_node_label(source)} {predicate} {_node_label(target)}"

    @staticmethod
    def _is_relation_heavy(query_text: str) -> bool:
        lowered = query_text.lower()
        return any(marker in lowered for marker in RELATION_QUERY_MARKERS)


def _node_label(node: GraphNode) -> str:
    entity_type = str(node.metadata.get("entity_type") or node.node_type)
    if entity_type in {"api_symbols", "pkcs11_objects", "pkcs11_mechanisms", "error_codes"}:
        return node.value
    return node.value.replace("_", " ")


def _safe_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
