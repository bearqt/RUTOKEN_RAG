from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchAny, MatchValue, PointStruct, VectorParams

from app.config import Settings
from app.domain.models import Chunk


class QdrantStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = QdrantClient(url=settings.qdrant_url)

    def ensure_collection(self, vector_size: int) -> None:
        existing = {collection.name for collection in self._client.get_collections().collections}
        if self._settings.qdrant_collection in existing:
            return
        self._client.create_collection(
            collection_name=self._settings.qdrant_collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def upsert_chunks(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        points = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            payload = {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "page_id": chunk.page_id,
                "source_url": chunk.source_url,
                "title": chunk.title,
                "heading_path": chunk.heading_path,
                "text": chunk.text,
                "chunk_type": chunk.chunk_type,
                **chunk.metadata,
            }
            point_id = str(uuid5(NAMESPACE_URL, chunk.chunk_id))
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))
        self._client.upsert(collection_name=self._settings.qdrant_collection, wait=True, points=points)

    def search(
        self,
        query_vector: list[float],
        top_k: int,
        filters: dict[str, list[str] | str],
    ) -> list[tuple[str, float]]:
        query_filter = self._build_filter(filters) if filters else None
        result = self._client.query_points(
            collection_name=self._settings.qdrant_collection,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        return [
            (str(point.payload["chunk_id"]), float(point.score))
            for point in result.points
            if point.payload and point.payload.get("chunk_id")
        ]

    def _build_filter(self, filters: dict[str, list[str] | str]) -> Filter:
        conditions = []
        for key, value in filters.items():
            if isinstance(value, list):
                conditions.append(FieldCondition(key=key, match=MatchAny(any=value)))
            else:
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        return Filter(must=conditions)
