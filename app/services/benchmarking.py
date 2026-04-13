from __future__ import annotations

import math
import re
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import Settings
from app.domain.models import PipelineResult
from app.services.benchmark_seed_data import get_seed_question_sets
from app.services.benchmark_repository import BenchmarkRepository
from app.services.pipeline import RagPipelineService
from app.services.research_question_sets import get_research_question_sets


REFUSAL_PATTERNS = (
    "в доступном контексте нет",
    "в контексте нет",
    "в предоставленном контексте нет",
    "нет данных",
    "недостаточно данных",
    "не удалось найти",
    "не найден",
    "не найдено",
)


RECALL_K = 5
RANKING_K = 10


@dataclass(slots=True)
class BenchmarkCase:
    case_id: str
    question: str
    question_id: str | None = None
    tags: list[str] = field(default_factory=list)
    reference_answer: str | None = None
    exact_answer: str | None = None
    required_terms: list[str] = field(default_factory=list)
    required_any: list[list[str]] = field(default_factory=list)
    forbidden_terms: list[str] = field(default_factory=list)
    required_sources: list[str] = field(default_factory=list)
    expected_refusal: bool = False
    notes: str | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "BenchmarkCase":
        case_id = record.get("case_key") or record.get("id")
        if not case_id:
            raise ValueError("Benchmark case must contain 'case_key' or 'id'")
        question = str(record.get("question", "")).strip()
        if not question:
            raise ValueError(f"Benchmark case {case_id!r} must contain a non-empty question")
        return cls(
            case_id=str(case_id),
            question=question,
            question_id=record.get("id"),
            tags=[str(item) for item in record.get("tags", [])],
            reference_answer=record.get("reference_answer"),
            exact_answer=record.get("exact_answer"),
            required_terms=[str(item) for item in record.get("required_terms", [])],
            required_any=[[str(item) for item in group] for group in record.get("required_any", [])],
            forbidden_terms=[str(item) for item in record.get("forbidden_terms", [])],
            required_sources=[str(item) for item in record.get("required_sources", [])],
            expected_refusal=bool(record.get("expected_refusal", False)),
            notes=record.get("notes"),
        )


class BenchmarkService:
    def __init__(self, settings: Settings, pipeline: RagPipelineService) -> None:
        self._settings = settings
        self._pipeline = pipeline
        self._repository = BenchmarkRepository(settings)

    def initialize(self) -> None:
        self._repository.ensure_schema()
        self._repository.ensure_seed_sets(get_seed_question_sets())
        self._repository.ensure_seed_sets(get_research_question_sets())

    def list_question_sets(self) -> list[dict]:
        return self._repository.list_question_sets()

    def get_question_set(self, set_id: str) -> dict | None:
        return self._repository.get_question_set(set_id)

    def create_question_set(self, payload: dict) -> dict:
        if not str(payload.get("name", "")).strip():
            raise ValueError("Question set name is required")
        return self._repository.create_question_set(payload)

    def update_question_set(self, set_id: str, payload: dict) -> dict | None:
        if not str(payload.get("name", "")).strip():
            raise ValueError("Question set name is required")
        return self._repository.update_question_set(set_id, payload)

    def list_runs(self, set_id: str | None = None, limit: int = 100) -> list[dict]:
        return self._repository.list_runs(set_id=set_id, limit=limit)

    def get_run(self, run_id: str) -> dict | None:
        return self._repository.get_run(run_id)

    def run(self, set_id: str, retrieval_mode: str = "hybrid") -> dict:
        question_set = self._repository.get_question_set(set_id)
        if question_set is None:
            raise FileNotFoundError(f"Question set is missing: {set_id}")
        cases = [BenchmarkCase.from_record(item) for item in question_set["questions"]]
        if not cases:
            raise ValueError("Question set does not contain any questions")
        results = [self._run_case(case, retrieval_mode) for case in cases]
        normalized_retrieval_mode = results[0]["actual"]["retrieval_mode"] if results else retrieval_mode
        summary = self._build_summary(results, normalized_retrieval_mode)
        return self._repository.save_run(
            set_id=set_id,
            set_name=question_set["name"],
            retrieval_mode=normalized_retrieval_mode,
            summary=summary,
            cases=results,
        )

    @staticmethod
    def dataset_preview(question_set: dict) -> dict:
        return {
            "id": question_set["id"],
            "name": question_set["name"],
            "description": question_set.get("description"),
            "questions": question_set.get("questions", []),
        }

    def _run_case(self, case: BenchmarkCase, retrieval_mode: str) -> dict:
        started_at = time.perf_counter()
        pipeline_result = self._pipeline.run(case.question, retrieval_mode=retrieval_mode)
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return self._evaluate_case(case, pipeline_result, latency_ms)

    def _evaluate_case(
        self,
        case: BenchmarkCase,
        result: PipelineResult,
        latency_ms: float,
    ) -> dict[str, Any]:
        normalized_answer = normalize_text(result.answer)
        ranked_chunks = result.ranked_chunks or result.retrieved_chunks
        retrieval_metrics = evaluate_retrieval_metrics(case.required_sources, ranked_chunks)
        actual_sources = [normalize_source(item.source_url) for item in result.citations]
        unique_sources = list(dict.fromkeys(actual_sources))

        missing_required_terms = [
            term for term in case.required_terms
            if normalize_text(term) not in normalized_answer
        ]
        missing_required_groups = [
            group for group in case.required_any
            if not any(normalize_text(term) in normalized_answer for term in group)
        ]
        unexpected_forbidden_terms = [
            term for term in case.forbidden_terms
            if normalize_text(term) in normalized_answer
        ]
        missing_sources = [
            source for source in case.required_sources
            if normalize_source(source) not in unique_sources
        ]

        actual_refusal = any(pattern in normalized_answer for pattern in REFUSAL_PATTERNS)
        exact_match_applicable = case.exact_answer is not None
        exact_match_passed = (
            normalize_text(case.exact_answer or "") == normalized_answer
            if exact_match_applicable
            else True
        )

        checks = {
            "exact_match": {
                "applicable": exact_match_applicable,
                "passed": exact_match_passed,
            },
            "required_terms": {
                "applicable": bool(case.required_terms),
                "passed": not missing_required_terms,
            },
            "required_any": {
                "applicable": bool(case.required_any),
                "passed": not missing_required_groups,
            },
            "forbidden_terms": {
                "applicable": bool(case.forbidden_terms),
                "passed": not unexpected_forbidden_terms,
            },
            "citations": {
                "applicable": bool(case.required_sources),
                "passed": not missing_sources,
            },
            "refusal": {
                "applicable": True,
                "passed": actual_refusal == case.expected_refusal,
            },
        }

        applicable_checks = [item for item in checks.values() if item["applicable"]]
        passed_checks = sum(1 for item in applicable_checks if item["passed"])
        overall_passed = all(item["passed"] for item in applicable_checks)
        score = round(passed_checks / len(applicable_checks), 4) if applicable_checks else 1.0

        return {
            "id": case.case_id,
            "question_id": case.question_id,
            "question": case.question,
            "tags": case.tags,
            "notes": case.notes,
            "expected": {
                "reference_answer": case.reference_answer,
                "exact_answer": case.exact_answer,
                "required_terms": case.required_terms,
                "required_any": case.required_any,
                "forbidden_terms": case.forbidden_terms,
                "required_sources": case.required_sources,
                "expected_refusal": case.expected_refusal,
            },
            "actual": {
                "rewritten_query": result.analysis.rewritten_query,
                "filters": result.analysis.filters,
                "query_mode": result.analysis.query_mode,
                "retrieval_mode": result.retrieval_mode,
                "routing_confidence": result.analysis.routing_confidence,
                "routing_reason": result.analysis.routing_reason,
                "answer": result.answer,
                "graph_facts": result.graph_facts,
                "citations": [
                    {
                        "source_url": item.source_url,
                        "title": item.title,
                        "heading_path": item.heading_path,
                        "chunk_id": item.chunk_id,
                    }
                    for item in result.citations
                ],
                "retrieved_source_urls": list(dict.fromkeys(item.chunk.source_url for item in result.retrieved_chunks)),
                "retrieved_chunks": [
                    {
                        "chunk_id": item.chunk.chunk_id,
                        "title": item.chunk.title,
                        "heading_path": item.chunk.heading_path,
                        "source_url": item.chunk.source_url,
                        "chunk_type": item.chunk.chunk_type,
                        "dense_score": item.dense_score,
                        "sparse_score": item.sparse_score,
                        "graph_score": item.graph_score,
                        "fused_score": item.fused_score,
                        "rerank_score": item.rerank_score,
                    }
                    for item in result.retrieved_chunks
                ],
                "retrieval_ranked_source_urls_top10": retrieval_metrics["ranked_source_urls_top10"],
                "retrieval_ranked_chunks_top10": [
                    {
                        "chunk_id": item.chunk.chunk_id,
                        "title": item.chunk.title,
                        "heading_path": item.chunk.heading_path,
                        "source_url": item.chunk.source_url,
                        "chunk_type": item.chunk.chunk_type,
                        "dense_score": item.dense_score,
                        "sparse_score": item.sparse_score,
                        "graph_score": item.graph_score,
                        "fused_score": item.fused_score,
                        "rerank_score": item.rerank_score,
                    }
                    for item in ranked_chunks[:RANKING_K]
                ],
                "latency_ms": latency_ms,
                "actual_refusal": actual_refusal,
            },
            "retrieval_metrics": retrieval_metrics,
            "checks": checks,
            "diagnostics": {
                "missing_required_terms": missing_required_terms,
                "missing_required_groups": missing_required_groups,
                "unexpected_forbidden_terms": unexpected_forbidden_terms,
                "missing_sources": missing_sources,
            },
            "score": score,
            "passed": overall_passed,
        }

    @staticmethod
    def _build_summary(results: list[dict[str, Any]], retrieval_mode: str) -> dict[str, Any]:
        total_cases = len(results)
        if not results:
            return {
                "retrieval_mode": retrieval_mode,
                "passed_cases": 0,
                "pass_rate": 0.0,
                "average_score": 0.0,
                "average_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "retrieval_metrics": {},
                "metrics": {},
                "per_tag": {},
            }

        latencies = [float(item["actual"]["latency_ms"]) for item in results]
        metric_names = ("exact_match", "required_terms", "required_any", "forbidden_terms", "citations", "refusal")
        metrics: dict[str, Any] = {}
        for name in metric_names:
            applicable = [item for item in results if item["checks"][name]["applicable"]]
            passed = [item for item in applicable if item["checks"][name]["passed"]]
            metrics[name] = {
                "applicable": len(applicable),
                "passed": len(passed),
                "rate": round(len(passed) / len(applicable), 4) if applicable else None,
            }

        retrieval_applicable = [
            item["retrieval_metrics"]
            for item in results
            if item.get("retrieval_metrics", {}).get("applicable")
        ]
        retrieval_summary = {
            "applicable": len(retrieval_applicable),
            "recall_at_5": round(statistics.mean(item["recall_at_5"] for item in retrieval_applicable), 4)
            if retrieval_applicable
            else None,
            "mrr_at_10": round(statistics.mean(item["mrr_at_10"] for item in retrieval_applicable), 4)
            if retrieval_applicable
            else None,
            "ndcg_at_10": round(statistics.mean(item["ndcg_at_10"] for item in retrieval_applicable), 4)
            if retrieval_applicable
            else None,
        }

        per_tag: dict[str, list[dict[str, Any]]] = {}
        for item in results:
            for tag in item.get("tags") or ["untagged"]:
                per_tag.setdefault(tag, []).append(item)

        return {
            "retrieval_mode": retrieval_mode,
            "passed_cases": sum(1 for item in results if item["passed"]),
            "pass_rate": round(sum(1 for item in results if item["passed"]) / total_cases, 4),
            "average_score": round(statistics.mean(item["score"] for item in results), 4),
            "average_latency_ms": round(statistics.mean(latencies), 2),
            "p95_latency_ms": round(percentile(latencies, 95), 2),
            "retrieval_metrics": retrieval_summary,
            "metrics": metrics,
            "per_tag": {
                tag: {
                    "total": len(items),
                    "passed": sum(1 for item in items if item["passed"]),
                    "pass_rate": round(sum(1 for item in items if item["passed"]) / len(items), 4),
                    "average_score": round(statistics.mean(item["score"] for item in items), 4),
                }
                for tag, items in per_tag.items()
            },
        }


def normalize_text(text: str) -> str:
    value = text.lower().replace("ё", "е")
    value = re.sub(r"`+", "", value)
    value = re.sub(r"[*_>#~]", " ", value)
    value = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", value)
    value = re.sub(r"[“”\"'«»]", " ", value)
    value = re.sub(r"[(),.;!?]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_source(source_url: str) -> str:
    return source_url.strip().rstrip("/").lower()


def evaluate_retrieval_metrics(required_sources: list[str], ranked_chunks: list[Any]) -> dict[str, Any]:
    relevant_sources = unique_preserve(
        normalize_source(source)
        for source in required_sources
        if str(source).strip()
    )
    ranked_source_urls = unique_preserve(
        normalize_source(item.chunk.source_url)
        for item in ranked_chunks
        if getattr(item.chunk, "source_url", None)
    )[:RANKING_K]

    if not relevant_sources:
        return {
            "applicable": False,
            "relevant_sources": [],
            "ranked_source_urls_top10": ranked_source_urls,
            "recall_at_5": None,
            "mrr_at_10": None,
            "ndcg_at_10": None,
        }

    relevant_set = set(relevant_sources)
    recall_hits = sum(1 for source in relevant_sources if source in ranked_source_urls[:RECALL_K])
    recall_at_5 = recall_hits / len(relevant_sources)

    reciprocal_rank = 0.0
    for rank, source in enumerate(ranked_source_urls[:RANKING_K], start=1):
        if source in relevant_set:
            reciprocal_rank = 1.0 / rank
            break

    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, source in enumerate(ranked_source_urls[:RANKING_K], start=1)
        if source in relevant_set
    )
    ideal_hits = min(len(relevant_sources), RANKING_K)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    ndcg_at_10 = dcg / idcg if idcg else 0.0

    return {
        "applicable": True,
        "relevant_sources": relevant_sources,
        "ranked_source_urls_top10": ranked_source_urls,
        "recall_at_5": round(recall_at_5, 4),
        "mrr_at_10": round(reciprocal_rank, 4),
        "ndcg_at_10": round(ndcg_at_10, 4),
    }


def unique_preserve(values: Any) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percent / 100
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight
