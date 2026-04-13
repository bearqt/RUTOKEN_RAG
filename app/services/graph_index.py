from __future__ import annotations

from app.config import Settings
from app.domain.models import Chunk
from app.services.graph_repository import GraphRepository
from app.services.storage import load_chunks


class GraphIndexService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._repository = GraphRepository(settings)

    def rebuild(self, chunks: list[Chunk]) -> None:
        if not self._settings.graph_enabled:
            return
        self._repository.ensure_schema()
        self._repository.replace_graph(chunks)

    def ensure_from_storage(self) -> None:
        if not self._settings.graph_enabled:
            return
        self._repository.ensure_schema()
        if self._repository.has_index():
            return
        chunks = load_chunks(self._settings.chunks_path)
        if not chunks:
            return
        self._repository.replace_graph(chunks)
