from __future__ import annotations

from app.config import Settings
from app.services.ingestion import IngestionService


def bootstrap_if_needed(settings: Settings) -> None:
    if not settings.auto_ingest_on_start:
        return
    if settings.manifest_path.exists() and settings.chunks_path.exists():
        return
    IngestionService(settings).ingest()

