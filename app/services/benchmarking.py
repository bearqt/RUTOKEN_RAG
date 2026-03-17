from __future__ import annotations

import json
import math
import re
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from app.domain.models import PipelineResult
from app.services.pipeline import RagPipelineService


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


@dataclass(slots=True)
class BenchmarkCase:
    case_id: str
    question: str
    tags: list[str] = field(default_factory=list)
    exact_answer: str | None = None
    required_terms: list[str] = field(default_factory=list)
    required_any: list[list[str]] = field(default_factory=list)
    forbidden_terms: list[str] = field(default_factory=list)
    required_sources: list[str] = field(default_factory=list)
    expected_refusal: bool = False
    notes: str | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "BenchmarkCase":
        case_id = record.get("id") or record.get("case_id")
        if not case_id:
            raise ValueError("Benchmark case must contain 'id'")
        question = str(record.get("question", "")).strip()
        if not question:
            raise ValueError(f"Benchmark case {case_id!r} must contain a non-empty question")
        return cls(
            case_id=str(case_id),
            question=question,
            tags=[str(item) for item in record.get("tags", [])],
            exact_answer=record.get("exact_answer"),
            required_terms=[str(item) for item in record.get("required_terms", [])],
            required_any=[[str(item) for item in group] for group in record.get("required_any", [])],
            forbidden_terms=[str(item) for item in record.get("forbidden_terms", [])],
            required_sources=[str(item) for item in record.get("required_sources", [])],
            expected_refusal=bool(record.get("expected_refusal", False)),
            notes=record.get("notes"),
        )


@dataclass(slots=True)
class BenchmarkRun:
    generated_at: str
    dataset_path: str
    total_cases: int
    summary: dict[str, Any]
    cases: list[dict[str, Any]]

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


class BenchmarkService:
    def __init__(self, settings: Settings, pipeline: RagPipelineService) -> None:
        self._settings = settings
        self._pipeline = pipeline

    def run(self, dataset_path: Path | None = None) -> BenchmarkRun:
        path = (dataset_path or self._settings.benchmark_dataset_path).resolve()
        cases = self._load_cases(path)
        results = [self._run_case(case) for case in cases]
        run = BenchmarkRun(
            generated_at=datetime.now(UTC).isoformat(),
            dataset_path=str(path),
            total_cases=len(results),
            summary=self._build_summary(results),
            cases=results,
        )
        self._settings.benchmark_results_path.write_text(
            json.dumps(run.to_record(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return run

    def load_last_run(self) -> dict[str, Any] | None:
        path = self._settings.benchmark_results_path
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def preview_cases(self, dataset_path: Path | None = None) -> list[dict[str, Any]]:
        path = (dataset_path or self._settings.benchmark_dataset_path).resolve()
        return [asdict(case) for case in self._load_cases(path)]

    def _load_cases(self, path: Path) -> list[BenchmarkCase]:
        if not path.exists():
            raise FileNotFoundError(f"Benchmark dataset is missing: {path}")
        loaded: list[BenchmarkCase] = []
        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    record = json.loads(stripped)
                except json.JSONDecodeError as error:
                    raise ValueError(f"Invalid JSONL in {path} at line {line_number}") from error
                loaded.append(BenchmarkCase.from_record(record))
        return loaded

    def _run_case(self, case: BenchmarkCase) -> dict[str, Any]:
        started_at = time.perf_counter()
        pipeline_result = self._pipeline.run(case.question)
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        evaluation = self._evaluate_case(case, pipeline_result, latency_ms)
        return evaluation

    def _evaluate_case(
        self,
        case: BenchmarkCase,
        result: PipelineResult,
        latency_ms: float,
    ) -> dict[str, Any]:
        normalized_answer = normalize_text(result.answer)
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

        required_terms_applicable = bool(case.required_terms)
        required_any_applicable = bool(case.required_any)
        forbidden_terms_applicable = bool(case.forbidden_terms)
        citation_applicable = bool(case.required_sources)
        refusal_applicable = True

        checks = {
            "exact_match": {
                "applicable": exact_match_applicable,
                "passed": exact_match_passed,
            },
            "required_terms": {
                "applicable": required_terms_applicable,
                "passed": not missing_required_terms,
            },
            "required_any": {
                "applicable": required_any_applicable,
                "passed": not missing_required_groups,
            },
            "forbidden_terms": {
                "applicable": forbidden_terms_applicable,
                "passed": not unexpected_forbidden_terms,
            },
            "citations": {
                "applicable": citation_applicable,
                "passed": not missing_sources,
            },
            "refusal": {
                "applicable": refusal_applicable,
                "passed": actual_refusal == case.expected_refusal,
            },
        }

        applicable_checks = [item for item in checks.values() if item["applicable"]]
        passed_checks = sum(1 for item in applicable_checks if item["passed"])
        overall_passed = all(item["passed"] for item in applicable_checks)
        score = round(passed_checks / len(applicable_checks), 4) if applicable_checks else 1.0

        retrieved_source_urls = list(
            dict.fromkeys(item.chunk.source_url for item in result.retrieved_chunks)
        )

        return {
            "id": case.case_id,
            "question": case.question,
            "tags": case.tags,
            "notes": case.notes,
            "expected": {
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
                "answer": result.answer,
                "citations": [
                    {
                        "source_url": item.source_url,
                        "title": item.title,
                        "heading_path": item.heading_path,
                        "chunk_id": item.chunk_id,
                    }
                    for item in result.citations
                ],
                "retrieved_source_urls": retrieved_source_urls,
                "retrieved_chunks": [
                    {
                        "chunk_id": item.chunk.chunk_id,
                        "title": item.chunk.title,
                        "heading_path": item.chunk.heading_path,
                        "source_url": item.chunk.source_url,
                        "chunk_type": item.chunk.chunk_type,
                        "dense_score": item.dense_score,
                        "sparse_score": item.sparse_score,
                        "fused_score": item.fused_score,
                        "rerank_score": item.rerank_score,
                    }
                    for item in result.retrieved_chunks
                ],
                "latency_ms": latency_ms,
                "actual_refusal": actual_refusal,
            },
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
    def _build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
        total_cases = len(results)
        if not results:
            return {
                "pass_rate": 0.0,
                "average_score": 0.0,
                "average_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "passed_cases": 0,
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

        per_tag: dict[str, list[dict[str, Any]]] = {}
        for item in results:
            tags = item.get("tags") or ["untagged"]
            for tag in tags:
                per_tag.setdefault(tag, []).append(item)

        per_tag_summary = {
            tag: {
                "total": len(items),
                "passed": sum(1 for item in items if item["passed"]),
                "pass_rate": round(sum(1 for item in items if item["passed"]) / len(items), 4),
                "average_score": round(statistics.mean(item["score"] for item in items), 4),
            }
            for tag, items in per_tag.items()
        }

        return {
            "passed_cases": sum(1 for item in results if item["passed"]),
            "pass_rate": round(sum(1 for item in results if item["passed"]) / total_cases, 4),
            "average_score": round(statistics.mean(item["score"] for item in results), 4),
            "average_latency_ms": round(statistics.mean(latencies), 2),
            "p95_latency_ms": round(percentile(latencies, 95), 2),
            "metrics": metrics,
            "per_tag": per_tag_summary,
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
