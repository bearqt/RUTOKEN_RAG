from __future__ import annotations

from collections import defaultdict

from app.config import Settings
from app.domain.graph_models import GraphChunkHit, GraphNode, GraphSearchResult, GraphSnapshot
from app.services.graph_repository import GraphRepository
from app.services.text_utils import unique_preserve


QUERY_MODE_FACTORS = {
    "classic": 0.0,
    "mixed": 1.0,
    "graph_first": 1.2,
}

SEED_TYPE_WEIGHTS = {
    "api_symbols": 1.8,
    "components": 1.25,
    "interfaces": 1.0,
    "products": 1.0,
    "os_tags": 0.7,
    "language_tags": 0.5,
}


class GraphSearchService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._repository = GraphRepository(settings)
        self._repository.ensure_schema()
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
    ) -> GraphSearchResult:
        if not self._settings.graph_enabled or query_mode == "classic":
            return GraphSearchResult()

        seed_nodes = self._seed_nodes(query_entities)
        if not seed_nodes:
            return GraphSearchResult()

        exact_entity_scores: dict[str, float] = defaultdict(float)
        for node in seed_nodes:
            exact_entity_scores[node.node_id] += SEED_TYPE_WEIGHTS.get(
                str(node.metadata.get("entity_type") or ""),
                0.8,
            )

        neighbor_scores: dict[str, float] = defaultdict(float)
        facts: list[str] = []
        expansion_factor = QUERY_MODE_FACTORS.get(query_mode, 1.0)
        for node in seed_nodes:
            neighbors = sorted(
                self._snapshot.entity_neighbors.get(node.node_id, []),
                key=lambda item: item[1],
                reverse=True,
            )[: self._settings.graph_neighbor_limit]
            for neighbor_id, edge_weight, edge_type in neighbors:
                neighbor = self._snapshot.nodes_by_id.get(neighbor_id)
                if neighbor is None:
                    continue
                neighbor_scores[neighbor_id] += min(edge_weight, 3.0) * 0.22 * expansion_factor
                facts.append(f"{_node_label(node)} -> {_node_label(neighbor)}")
                if edge_type == "entity_cooccurs_with_entity" and neighbor_id in exact_entity_scores:
                    facts.append(f"{_node_label(neighbor)} <-> {_node_label(node)}")

        combined_entity_scores = dict(exact_entity_scores)
        for neighbor_id, score in neighbor_scores.items():
            combined_entity_scores[neighbor_id] = combined_entity_scores.get(neighbor_id, 0.0) + score

        chunk_scores: dict[str, float] = defaultdict(float)
        document_scores: dict[str, float] = defaultdict(float)
        chunk_exact_matches: dict[str, set[str]] = defaultdict(set)

        for entity_id, entity_score in combined_entity_scores.items():
            for link in self._snapshot.entity_to_chunks.get(entity_id, []):
                chunk_scores[link.chunk_id] += entity_score * link.weight
                document_scores[link.document_id] += entity_score * 0.3
                if entity_id in exact_entity_scores:
                    chunk_exact_matches[link.chunk_id].add(entity_id)

        for chunk_id in list(chunk_scores):
            document_id = self._snapshot.chunk_to_document.get(chunk_id)
            if document_id:
                chunk_scores[chunk_id] += document_scores.get(document_id, 0.0) * self._settings.graph_document_boost
            exact_hits = len(chunk_exact_matches.get(chunk_id, set()))
            if exact_hits > 1:
                chunk_scores[chunk_id] += min(exact_hits, 4) * 0.2
            if query_mode == "graph_first":
                chunk_scores[chunk_id] *= 1.15

        ranked_hits = sorted(
            (GraphChunkHit(chunk_id=chunk_id, score=round(score, 4)) for chunk_id, score in chunk_scores.items() if score > 0),
            key=lambda item: item.score,
            reverse=True,
        )[:top_k]

        return GraphSearchResult(
            hits=ranked_hits,
            facts=unique_preserve(facts)[: self._settings.graph_fact_limit],
        )

    def _seed_nodes(self, query_entities: dict[str, list[str]]) -> list[GraphNode]:
        seeds: list[GraphNode] = []
        for entity_type, values in query_entities.items():
            if entity_type not in SEED_TYPE_WEIGHTS:
                continue
            for value in values:
                node = self._snapshot.nodes_by_id.get(f"{entity_type}:{value}")
                if node is not None:
                    seeds.append(node)
        return seeds


def _node_label(node: GraphNode) -> str:
    entity_type = str(node.metadata.get("entity_type") or node.node_type)
    if entity_type == "api_symbols":
        return node.value
    return node.value.replace("_", " ")
