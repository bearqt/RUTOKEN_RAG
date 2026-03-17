from __future__ import annotations

import json
from dataclasses import dataclass

from app.config import Settings
from app.domain.models import Chunk
from app.providers.gigachat import GigaChatEmbeddingsProvider
from app.retrieval.bm25_index import BM25Index
from app.retrieval.qdrant_store import QdrantStore
from app.services.parsing import build_chunks, load_source_documents
from app.services.storage import save_chunks


@dataclass(slots=True)
class IngestionResult:
    documents: int
    chunks: int
    vector_size: int


class IngestionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._embeddings = GigaChatEmbeddingsProvider(settings)
        self._qdrant = QdrantStore(settings)

    def ingest(self) -> IngestionResult:
        documents = load_source_documents(self._settings.scrape_dir)
        chunks: list[Chunk] = []
        for document in documents:
            chunks.extend(
                build_chunks(
                    document=document,
                    chunk_target_chars=self._settings.chunk_target_chars,
                    chunk_overlap_chars=self._settings.chunk_overlap_chars,
                    table_row_window=self._settings.table_row_window,
                )
            )

        vectors = self._embed_chunks(chunks)
        vector_size = len(vectors[0]) if vectors else 0
        if vector_size:
            self._qdrant.ensure_collection(vector_size)
            self._qdrant.upsert_chunks(chunks, vectors)

        save_chunks(self._settings.chunks_path, chunks)
        bm25 = BM25Index(chunks)
        bm25.save(self._settings.bm25_path)

        manifest = {
            "documents": len(documents),
            "chunks": len(chunks),
            "vector_size": vector_size,
        }
        self._settings.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return IngestionResult(documents=len(documents), chunks=len(chunks), vector_size=vector_size)

    def _embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        if not chunks:
            return []
        batch_size = 16
        vectors: list[list[float]] = []
        for index in range(0, len(chunks), batch_size):
            batch = chunks[index : index + batch_size]
            vectors.extend(self._embeddings.embed_texts([chunk.text for chunk in batch]))
        return vectors

