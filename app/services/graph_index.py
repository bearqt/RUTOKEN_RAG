from __future__ import annotations

from collections import defaultdict

from app.config import Settings
from app.domain.models import Chunk
from app.providers.embeddings import OpenRouterEmbeddingsProvider
from app.services.graph_repository import ENTITY_KEYS, GraphRepository
from app.services.graph_vector_store import GraphVectorStore
from app.services.ner import entity_aliases
from app.services.storage import load_chunks
from app.services.text_utils import unique_preserve


class GraphIndexService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._repository = GraphRepository(settings)
        self._vector_store = GraphVectorStore(settings)
        self._embeddings = OpenRouterEmbeddingsProvider(settings)

    def rebuild(self, chunks: list[Chunk]) -> None:
        if not self._settings.graph_enabled:
            return
        self._repository.ensure_schema()
        self._repository.replace_graph(chunks)
        self._rebuild_vector_indices(chunks)

    def ensure_from_storage(self) -> None:
        if not self._settings.graph_enabled:
            return
        self._repository.ensure_schema()
        chunks = load_chunks(self._settings.chunks_path)
        if not chunks:
            return
        if not self._repository.has_index():
            self._repository.replace_graph(chunks)
        if not self._vector_store.has_indices():
            self._rebuild_vector_indices(chunks)

    def _rebuild_vector_indices(self, chunks: list[Chunk]) -> None:
        if not chunks or not self._embeddings.is_configured():
            return

        entity_records = self._build_entity_records(chunks)
        if entity_records:
            entity_vectors = self._embeddings.embed_texts([record["content"] for record in entity_records])
            self._vector_store.rebuild_entities(entity_records, entity_vectors)
        else:
            self._vector_store.rebuild_entities([], [])

        relation_records = self._build_relation_records(chunks)
        if relation_records:
            relation_vectors = self._embeddings.embed_texts([record["content"] for record in relation_records])
            self._vector_store.rebuild_relations(relation_records, relation_vectors)
        else:
            self._vector_store.rebuild_relations([], [])

    def _build_entity_records(self, chunks: list[Chunk]) -> list[dict]:
        snippets_by_entity: dict[str, list[str]] = defaultdict(list)
        documents_by_entity: dict[str, set[str]] = defaultdict(set)
        chunks_by_entity: dict[str, set[str]] = defaultdict(set)
        entity_types: dict[str, str] = {}

        for chunk in chunks:
            snippet = " ".join(
                part
                for part in (
                    chunk.title,
                    " > ".join(chunk.heading_path),
                    str(chunk.metadata.get("doc_family") or ""),
                )
                if part
            ).strip()
            for entity_type in ENTITY_KEYS:
                for value in chunk.metadata.get(entity_type, []):
                    entity_id = f"{entity_type}:{value}"
                    entity_types[entity_id] = entity_type
                    if snippet:
                        snippets_by_entity[entity_id].append(snippet)
                    documents_by_entity[entity_id].add(chunk.document_id)
                    chunks_by_entity[entity_id].add(chunk.chunk_id)

        records: list[dict] = []
        for entity_id, entity_type in entity_types.items():
            canonical_value = entity_id.split(":", 1)[1]
            aliases = entity_aliases(entity_type, canonical_value)
            snippets = unique_preserve(snippets_by_entity.get(entity_id, []))[:3]
            description = " ".join(snippets).strip()
            content = " ".join(
                part
                for part in [entity_type, canonical_value, " ".join(aliases), description]
                if part
            ).strip()
            if not content:
                continue
            records.append(
                {
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "canonical_value": canonical_value,
                    "aliases": aliases,
                    "description": description,
                    "confidence": 1.0,
                    "document_frequency": len(documents_by_entity[entity_id]),
                    "chunk_frequency": len(chunks_by_entity[entity_id]),
                    "content": content,
                }
            )
        return records

    def _build_relation_records(self, chunks: list[Chunk]) -> list[dict]:
        relation_evidence: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        relation_docs: dict[tuple[str, str, str], set[str]] = defaultdict(set)
        relation_confidence: dict[tuple[str, str, str], float] = defaultdict(float)
        relation_types: dict[tuple[str, str, str], tuple[str, str, str, str, str]] = {}

        for chunk in chunks:
            relations = chunk.metadata.get("graph_relations", [])
            if not isinstance(relations, list):
                continue
            for relation in relations:
                if not isinstance(relation, dict):
                    continue
                src_type = str(relation.get("src_type") or "").strip()
                src_value = str(relation.get("src_value") or "").strip()
                predicate = str(relation.get("predicate") or "").strip()
                tgt_type = str(relation.get("tgt_type") or "").strip()
                tgt_value = str(relation.get("tgt_value") or "").strip()
                if not src_type or not src_value or not predicate or not tgt_type or not tgt_value:
                    continue
                key = (f"{src_type}:{src_value}", f"{tgt_type}:{tgt_value}", predicate)
                relation_types[key] = (src_type, src_value, predicate, tgt_type, tgt_value)
                evidence = str(relation.get("evidence") or "").strip()
                if evidence:
                    relation_evidence[key].append(evidence)
                relation_docs[key].add(chunk.document_id)
                relation_confidence[key] = max(
                    relation_confidence[key],
                    _safe_float(relation.get("confidence"), 0.0),
                )

        records: list[dict] = []
        for key, relation_type in relation_types.items():
            src_type, src_value, predicate, tgt_type, tgt_value = relation_type
            evidence_samples = unique_preserve(relation_evidence.get(key, []))[:3]
            description = " ".join(evidence_samples).strip()
            content = " ".join(
                part
                for part in [
                    predicate,
                    src_type,
                    src_value,
                    tgt_type,
                    tgt_value,
                    description,
                ]
                if part
            ).strip()
            if not content:
                continue
            records.append(
                {
                    "relation_id": f"{key[0]}|{predicate}|{key[1]}",
                    "src_id": key[0],
                    "tgt_id": key[1],
                    "predicate": predicate,
                    "description": description,
                    "confidence": relation_confidence[key],
                    "document_frequency": len(relation_docs[key]),
                    "content": content,
                }
            )
        return records


def _safe_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
