from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.config import Settings
from app.domain.models import Chunk
from app.prompts.graph_enrichment import (
    GRAPH_ENRICHMENT_PROMPT_VERSION,
    GRAPH_ENRICHMENT_SYSTEM_PROMPT,
    build_graph_enrichment_prompt,
)
from app.providers.embeddings import ProviderConfigurationError
from app.providers.openrouter import OpenRouterProvider
from app.services.entity_canonicalizer import EntityCanonicalizer
from app.services.ner import ENTITY_FIELDS, entity_terms


class OfflineGraphEnrichmentService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._provider = OpenRouterProvider(settings)
        self._canonicalizer = EntityCanonicalizer()
        self._cache_path = settings.graph_enrichment_cache_path
        self._cache = self._load_cache(self._cache_path)

    def enrich_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        if not self._settings.graph_llm_enrichment_enabled:
            return chunks
        if not self._provider.is_configured():
            return chunks

        for chunk in chunks:
            if not self._should_enrich(chunk):
                continue
            response = self._resolve_response(chunk)
            if not isinstance(response, dict) or not response:
                continue
            self._apply_response(chunk, response)
        return chunks

    def _resolve_response(self, chunk: Chunk) -> dict | None:
        cache_key = self._cache_key(chunk)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            response = self._provider.complete_json(
                GRAPH_ENRICHMENT_SYSTEM_PROMPT,
                build_graph_enrichment_prompt(chunk),
            )
        except (ProviderConfigurationError, RuntimeError, ValueError, Exception):
            return None

        self._cache[cache_key] = response
        self._append_cache_record(cache_key, response)
        return response

    def _apply_response(self, chunk: Chunk, response: dict) -> None:
        rule_entities = chunk.metadata.get("graph_entities_rule", {})
        llm_entities = self._canonicalizer.canonicalize_entities(response.get("entities"))
        merged_entities = self._canonicalizer.merge_entities(rule_entities, llm_entities)
        relations = self._canonicalizer.canonicalize_relations(
            response.get("relations"),
            known_entities=merged_entities,
            confidence_threshold=self._settings.graph_llm_confidence_threshold,
        )

        for entity_type in ENTITY_FIELDS:
            chunk.metadata[entity_type] = merged_entities.get(entity_type, [])

        chunk.metadata["entity_terms"] = entity_terms(merged_entities)
        chunk.metadata["graph_entities_llm"] = llm_entities
        chunk.metadata["graph_relations"] = relations
        chunk.metadata["graph_enrichment_version"] = 1

    def _should_enrich(self, chunk: Chunk) -> bool:
        if chunk.chunk_type in {"reference", "table"}:
            return True
        if chunk.chunk_type == "prose":
            return len(chunk.text) >= self._settings.graph_enrichment_min_prose_chars
        if chunk.chunk_type == "code":
            markers = ("C_", "CKA_", "CKR_", "CKM_")
            return any(marker in chunk.text for marker in markers)
        return False

    def _cache_key(self, chunk: Chunk) -> str:
        digest = hashlib.sha256()
        digest.update(chunk.chunk_id.encode("utf-8"))
        digest.update(chunk.title.encode("utf-8"))
        digest.update("||".join(chunk.heading_path).encode("utf-8"))
        digest.update(chunk.chunk_type.encode("utf-8"))
        digest.update(chunk.text.encode("utf-8"))
        digest.update((self._settings.openrouter_model or "").encode("utf-8"))
        digest.update(GRAPH_ENRICHMENT_PROMPT_VERSION.encode("utf-8"))
        return digest.hexdigest()

    @staticmethod
    def _load_cache(path: Path) -> dict[str, dict]:
        cache: dict[str, dict] = {}
        if not path.exists():
            return cache
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = str(record.get("key") or "")
                response = record.get("response")
                if key and isinstance(response, dict):
                    cache[key] = response
        return cache

    def _append_cache_record(self, key: str, response: dict) -> None:
        with self._cache_path.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(
                    {"key": key, "response": response},
                    ensure_ascii=False,
                )
                + "\n"
            )
