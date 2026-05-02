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


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    return float(raw)


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
    openrouter_embedding_model: str | None = os.getenv("OPENROUTER_EMBEDDING_MODEL")
    openrouter_site_url: str | None = os.getenv("OPENROUTER_SITE_URL")
    openrouter_app_name: str | None = os.getenv("OPENROUTER_APP_NAME")

    benchmark_database_url: str = os.getenv(
        "BENCHMARK_DATABASE_URL",
        "postgresql://rutoken:rutoken@localhost:5432/rutoken_rag",
    )
    benchmark_seed_path: Path = _get_path("BENCHMARK_SEED_PATH", "./benchmark/dataset.jsonl")

    reranker_model: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    auto_ingest_on_start: bool = _get_bool("AUTO_INGEST_ON_START", False)
    graph_enabled: bool = _get_bool("GRAPH_ENABLED", True)
    graph_llm_enrichment_enabled: bool = _get_bool("GRAPH_LLM_ENRICHMENT_ENABLED", False)

    chunk_target_chars: int = _get_int("CHUNK_TARGET_CHARS", 2200)
    chunk_overlap_chars: int = _get_int("CHUNK_OVERLAP_CHARS", 250)
    table_row_window: int = _get_int("TABLE_ROW_WINDOW", 6)
    dense_candidate_count: int = _get_int("DENSE_CANDIDATE_COUNT", 20)
    sparse_candidate_count: int = _get_int("SPARSE_CANDIDATE_COUNT", 20)
    graph_candidate_count: int = _get_int("GRAPH_CANDIDATE_COUNT", 20)
    graph_neighbor_limit: int = _get_int("GRAPH_NEIGHBOR_LIMIT", 10)
    graph_fact_limit: int = _get_int("GRAPH_FACT_LIMIT", 8)
    graph_fusion_weight: float = _get_float("GRAPH_FUSION_WEIGHT", 0.4)
    graph_document_boost: float = _get_float("GRAPH_DOCUMENT_BOOST", 0.3)
    graph_exact_entity_weight: float = _get_float("GRAPH_EXACT_ENTITY_WEIGHT", 1.0)
    graph_semantic_entity_weight: float = _get_float("GRAPH_SEMANTIC_ENTITY_WEIGHT", 0.65)
    graph_relation_weight: float = _get_float("GRAPH_RELATION_WEIGHT", 0.85)
    graph_hub_penalty_alpha: float = _get_float("GRAPH_HUB_PENALTY_ALPHA", 0.18)
    graph_reference_chunk_boost: float = _get_float("GRAPH_REFERENCE_CHUNK_BOOST", 0.25)
    graph_section_neighbor_boost: float = _get_float("GRAPH_SECTION_NEIGHBOR_BOOST", 0.08)
    graph_final_fusion_weight: float = _get_float("GRAPH_FINAL_FUSION_WEIGHT", 0.18)
    graph_llm_confidence_threshold: float = _get_float("GRAPH_LLM_CONFIDENCE_THRESHOLD", 0.7)
    graph_enrichment_min_prose_chars: int = _get_int("GRAPH_ENRICHMENT_MIN_PROSE_CHARS", 500)
    graph_entity_top_k: int = _get_int("GRAPH_ENTITY_TOP_K", 8)
    graph_relation_top_k: int = _get_int("GRAPH_RELATION_TOP_K", 8)
    rerank_candidate_count: int = _get_int("RERANK_CANDIDATE_COUNT", 20)
    final_context_count: int = _get_int("FINAL_CONTEXT_COUNT", 5)

    chunks_path: Path = _get_path("CHUNKS_PATH", "./data/chunks.jsonl")
    bm25_path: Path = _get_path("BM25_PATH", "./data/bm25_index.json")
    manifest_path: Path = _get_path("MANIFEST_PATH", "./data/index_manifest.json")
    graph_enrichment_cache_path: Path = _get_path(
        "GRAPH_ENRICHMENT_CACHE_PATH",
        "./data/graph_enrichment_cache.jsonl",
    )
    graph_entity_collection: str = os.getenv("GRAPH_ENTITY_COLLECTION", "rutoken_graph_entities")
    graph_relation_collection: str = os.getenv("GRAPH_RELATION_COLLECTION", "rutoken_graph_relations")

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_path.parent.mkdir(parents=True, exist_ok=True)
        self.graph_enrichment_cache_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
