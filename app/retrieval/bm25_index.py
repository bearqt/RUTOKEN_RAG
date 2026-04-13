from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.domain.models import Chunk
from app.services.enrichment import metadata_matches
from app.services.text_utils import tokenize_for_bm25


@dataclass(slots=True)
class SparseHit:
    chunk_id: str
    score: float


class BM25Index:
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = {chunk.chunk_id: chunk for chunk in chunks}
        self._chunk_ids = [chunk.chunk_id for chunk in chunks]
        self._tokenized = [self._document_tokens(chunk) for chunk in chunks]
        self._index = BM25Okapi(self._tokenized) if chunks else None

    @classmethod
    def load(cls, path: Path, chunks: list[Chunk]) -> "BM25Index":
        if not path.exists():
            return cls(chunks)
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        instance = cls.__new__(cls)
        instance._chunks = {chunk.chunk_id: chunk for chunk in chunks}
        instance._chunk_ids = payload["chunk_ids"]
        instance._tokenized = payload["tokenized"]
        instance._index = BM25Okapi(instance._tokenized) if instance._tokenized else None
        return instance

    def save(self, path: Path) -> None:
        payload = {
            "chunk_ids": self._chunk_ids,
            "tokenized": self._tokenized,
        }
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False)

    def search(self, query: str, top_k: int, filters: dict[str, list[str] | str]) -> list[SparseHit]:
        if self._index is None:
            return []
        tokens = tokenize_for_bm25(query)
        scores = self._index.get_scores(tokens)
        pairs = sorted(
            (
                SparseHit(chunk_id=self._chunk_ids[index], score=float(score))
                for index, score in enumerate(scores)
                if score > 0
            ),
            key=lambda item: item.score,
            reverse=True,
        )
        filtered: list[SparseHit] = []
        for item in pairs:
            chunk = self._chunks.get(item.chunk_id)
            if chunk is None:
                continue
            if filters and not metadata_matches(chunk.metadata, filters):
                continue
            filtered.append(item)
            if len(filtered) >= top_k:
                break
        return filtered

    @staticmethod
    def _document_tokens(chunk: Chunk) -> list[str]:
        symbols = " ".join(chunk.metadata.get("api_symbols", []))
        entities = " ".join(chunk.metadata.get("entity_terms", []))
        heading = " ".join(chunk.heading_path)
        augmented = f"{chunk.title}\n{heading}\n{chunk.text}\n{symbols}\n{entities}"
        return tokenize_for_bm25(augmented)
