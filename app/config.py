from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def _get_path(name: str, default: str) -> Path:
    raw = os.getenv(name)
    path = Path(raw) if raw is not None else Path(default)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


@dataclass(frozen=True)
class Settings:
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = _get_int("APP_PORT", 8000)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    scrape_dir: Path = _get_path("SCRAPE_DIR", "./scrape_result")
    data_dir: Path = _get_path("DATA_DIR", "./data")

    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "rutoken_docs")

    gigachat_auth_url: str = os.getenv(
        "GIGACHAT_AUTH_URL",
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
    )
    gigachat_base_url: str = os.getenv(
        "GIGACHAT_BASE_URL",
        "https://gigachat.devices.sberbank.ru/api/v1",
    )
    gigachat_auth_key: str | None = os.getenv("GIGACHAT_AUTH_KEY")
    gigachat_scope: str = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
    gigachat_embedding_model: str = os.getenv("GIGACHAT_EMBEDDING_MODEL", "Embeddings-2")
    gigachat_verify_ssl: bool = _get_bool("GIGACHAT_VERIFY_SSL", True)

    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    openrouter_model: str | None = os.getenv("OPENROUTER_MODEL")
    openrouter_site_url: str | None = os.getenv("OPENROUTER_SITE_URL")
    openrouter_app_name: str | None = os.getenv("OPENROUTER_APP_NAME")

    reranker_model: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    auto_ingest_on_start: bool = _get_bool("AUTO_INGEST_ON_START", False)

    chunk_target_chars: int = _get_int("CHUNK_TARGET_CHARS", 2200)
    chunk_overlap_chars: int = _get_int("CHUNK_OVERLAP_CHARS", 250)
    table_row_window: int = _get_int("TABLE_ROW_WINDOW", 6)
    dense_candidate_count: int = _get_int("DENSE_CANDIDATE_COUNT", 20)
    sparse_candidate_count: int = _get_int("SPARSE_CANDIDATE_COUNT", 20)
    rerank_candidate_count: int = _get_int("RERANK_CANDIDATE_COUNT", 20)
    final_context_count: int = _get_int("FINAL_CONTEXT_COUNT", 5)

    chunks_path: Path = _get_path("CHUNKS_PATH", "./data/chunks.jsonl")
    bm25_path: Path = _get_path("BM25_PATH", "./data/bm25_index.json")
    manifest_path: Path = _get_path("MANIFEST_PATH", "./data/index_manifest.json")
    benchmark_dataset_path: Path = _get_path("BENCHMARK_DATASET_PATH", "./benchmark/dataset.jsonl")
    benchmark_results_path: Path = _get_path("BENCHMARK_RESULTS_PATH", "./data/benchmark_results.json")

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_path.parent.mkdir(parents=True, exist_ok=True)
        self.benchmark_results_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
