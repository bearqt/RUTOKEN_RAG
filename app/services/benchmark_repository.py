from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import Settings


class BenchmarkRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def ensure_schema(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS benchmark_question_sets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS benchmark_questions (
                id TEXT PRIMARY KEY,
                set_id TEXT NOT NULL REFERENCES benchmark_question_sets(id) ON DELETE CASCADE,
                case_key TEXT NOT NULL,
                position INTEGER NOT NULL,
                question TEXT NOT NULL,
                tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                reference_answer TEXT,
                exact_answer TEXT,
                required_terms JSONB NOT NULL DEFAULT '[]'::jsonb,
                required_any JSONB NOT NULL DEFAULT '[]'::jsonb,
                forbidden_terms JSONB NOT NULL DEFAULT '[]'::jsonb,
                required_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
                expected_refusal BOOLEAN NOT NULL DEFAULT FALSE,
                notes TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (set_id, case_key)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS benchmark_runs (
                id TEXT PRIMARY KEY,
                set_id TEXT NOT NULL REFERENCES benchmark_question_sets(id) ON DELETE RESTRICT,
                set_name TEXT NOT NULL,
                retrieval_mode TEXT NOT NULL DEFAULT 'hybrid',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                total_cases INTEGER NOT NULL,
                passed_cases INTEGER NOT NULL,
                pass_rate DOUBLE PRECISION NOT NULL,
                average_score DOUBLE PRECISION NOT NULL,
                average_latency_ms DOUBLE PRECISION NOT NULL,
                p95_latency_ms DOUBLE PRECISION NOT NULL,
                summary JSONB NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS benchmark_run_cases (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES benchmark_runs(id) ON DELETE CASCADE,
                question_id TEXT,
                case_key TEXT NOT NULL,
                case_order INTEGER NOT NULL,
                passed BOOLEAN NOT NULL,
                score DOUBLE PRECISION NOT NULL,
                evaluation JSONB NOT NULL
            )
            """,
        ]
        with self._connect() as conn:
            for statement in statements:
                conn.execute(statement)
            conn.execute("ALTER TABLE benchmark_questions ADD COLUMN IF NOT EXISTS reference_answer TEXT")
            conn.execute("ALTER TABLE benchmark_runs ADD COLUMN IF NOT EXISTS retrieval_mode TEXT NOT NULL DEFAULT 'hybrid'")

    def seed_if_empty(self, seed_path: Path) -> None:
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS count FROM benchmark_question_sets").fetchone()["count"]
            if count:
                return
        if not seed_path.exists():
            return

        questions: list[dict] = []
        with seed_path.open("r", encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if stripped:
                    questions.append(json.loads(stripped))

        if not questions:
            return

        self.create_question_set(
            {
                "name": "Seed dataset",
                "description": "Импортировано из benchmark/dataset.jsonl",
                "questions": [
                    {
                        "case_key": item.get("id") or item.get("case_key"),
                        "question": item.get("question", ""),
                        "tags": item.get("tags", []),
                        "reference_answer": item.get("reference_answer"),
                        "exact_answer": item.get("exact_answer"),
                        "required_terms": item.get("required_terms", []),
                        "required_any": item.get("required_any", []),
                        "forbidden_terms": item.get("forbidden_terms", []),
                        "required_sources": item.get("required_sources", []),
                        "expected_refusal": item.get("expected_refusal", False),
                        "notes": item.get("notes"),
                    }
                    for item in questions
                ],
            }
        )

    def ensure_seed_sets(self, question_sets: list[dict]) -> None:
        if not question_sets:
            return
        with self._connect() as conn:
            existing_ids = {
                row["id"]
                for row in conn.execute("SELECT id FROM benchmark_question_sets").fetchall()
            }
            for payload in question_sets:
                set_id = str(payload["id"]).strip()
                if not set_id or set_id in existing_ids:
                    continue
                conn.execute(
                    """
                    INSERT INTO benchmark_question_sets (id, name, description)
                    VALUES (%s, %s, %s)
                    """,
                    (set_id, payload["name"].strip(), payload.get("description")),
                )
                self._replace_questions(
                    conn,
                    set_id,
                    self._normalize_questions(payload.get("questions", [])),
                )
                existing_ids.add(set_id)

    def list_question_sets(self) -> list[dict]:
        query = """
        SELECT
            s.id,
            s.name,
            s.description,
            s.created_at,
            s.updated_at,
            COALESCE(q.question_count, 0) AS question_count,
            r.last_run_at
        FROM benchmark_question_sets AS s
        LEFT JOIN (
            SELECT set_id, COUNT(*) AS question_count
            FROM benchmark_questions
            GROUP BY set_id
        ) AS q ON q.set_id = s.id
        LEFT JOIN (
            SELECT set_id, MAX(created_at) AS last_run_at
            FROM benchmark_runs
            GROUP BY set_id
        ) AS r ON r.set_id = s.id
        ORDER BY s.updated_at DESC, s.created_at DESC
        """
        with self._connect() as conn:
            rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]

    def get_question_set(self, set_id: str) -> dict | None:
        with self._connect() as conn:
            set_row = conn.execute(
                """
                SELECT id, name, description, created_at, updated_at
                FROM benchmark_question_sets
                WHERE id = %s
                """,
                (set_id,),
            ).fetchone()
            if set_row is None:
                return None

            question_rows = conn.execute(
                """
                SELECT
                    id,
                    case_key,
                    position,
                    question,
                    tags,
                    reference_answer,
                    exact_answer,
                    required_terms,
                    required_any,
                    forbidden_terms,
                    required_sources,
                    expected_refusal,
                    notes,
                    created_at,
                    updated_at
                FROM benchmark_questions
                WHERE set_id = %s
                ORDER BY position ASC, created_at ASC
                """,
                (set_id,),
            ).fetchall()
        payload = dict(set_row)
        payload["questions"] = [dict(row) for row in question_rows]
        return payload

    def create_question_set(self, payload: dict) -> dict:
        questions = self._normalize_questions(payload.get("questions", []))
        set_id = str(uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO benchmark_question_sets (id, name, description)
                VALUES (%s, %s, %s)
                """,
                (set_id, payload["name"].strip(), payload.get("description")),
            )
            self._replace_questions(conn, set_id, questions)
        created = self.get_question_set(set_id)
        if created is None:
            raise RuntimeError("Created question set could not be loaded")
        return created

    def update_question_set(self, set_id: str, payload: dict) -> dict | None:
        questions = self._normalize_questions(payload.get("questions", []))
        with self._connect() as conn:
            updated = conn.execute(
                """
                UPDATE benchmark_question_sets
                SET name = %s, description = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id
                """,
                (payload["name"].strip(), payload.get("description"), set_id),
            ).fetchone()
            if updated is None:
                return None
            conn.execute("DELETE FROM benchmark_questions WHERE set_id = %s", (set_id,))
            self._replace_questions(conn, set_id, questions)
        return self.get_question_set(set_id)

    def list_runs(self, set_id: str | None = None, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            if set_id:
                rows = conn.execute(
                    """
                    SELECT id, set_id, set_name, COALESCE(retrieval_mode, 'hybrid') AS retrieval_mode, created_at, total_cases, passed_cases, pass_rate,
                           average_score, average_latency_ms, p95_latency_ms
                    FROM benchmark_runs
                    WHERE set_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (set_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, set_id, set_name, COALESCE(retrieval_mode, 'hybrid') AS retrieval_mode, created_at, total_cases, passed_cases, pass_rate,
                           average_score, average_latency_ms, p95_latency_ms
                    FROM benchmark_runs
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                ).fetchall()
        return [dict(row) for row in rows]

    def get_run(self, run_id: str) -> dict | None:
        with self._connect() as conn:
            run_row = conn.execute(
                """
                SELECT id, set_id, set_name, COALESCE(retrieval_mode, 'hybrid') AS retrieval_mode, created_at, total_cases, passed_cases, pass_rate,
                       average_score, average_latency_ms, p95_latency_ms, summary
                FROM benchmark_runs
                WHERE id = %s
                """,
                (run_id,),
            ).fetchone()
            if run_row is None:
                return None
            case_rows = conn.execute(
                """
                SELECT case_key, question_id, case_order, passed, score, evaluation
                FROM benchmark_run_cases
                WHERE run_id = %s
                ORDER BY case_order ASC
                """,
                (run_id,),
            ).fetchall()
        payload = dict(run_row)
        payload["cases"] = [row["evaluation"] for row in case_rows]
        return payload

    def save_run(self, set_id: str, set_name: str, retrieval_mode: str, summary: dict, cases: list[dict]) -> dict:
        run_id = str(uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO benchmark_runs (
                    id, set_id, set_name, retrieval_mode, total_cases, passed_cases, pass_rate,
                    average_score, average_latency_ms, p95_latency_ms, summary
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    set_id,
                    set_name,
                    retrieval_mode,
                    len(cases),
                    summary["passed_cases"],
                    summary["pass_rate"],
                    summary["average_score"],
                    summary["average_latency_ms"],
                    summary["p95_latency_ms"],
                    Jsonb(summary),
                ),
            )
            for index, case in enumerate(cases, start=1):
                conn.execute(
                    """
                    INSERT INTO benchmark_run_cases (
                        id, run_id, question_id, case_key, case_order, passed, score, evaluation
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid4()),
                        run_id,
                        case.get("question_id"),
                        case["id"],
                        index,
                        case["passed"],
                        case["score"],
                        Jsonb(case),
                    ),
                )
        stored = self.get_run(run_id)
        if stored is None:
            raise RuntimeError("Saved benchmark run could not be loaded")
        return stored

    def _replace_questions(self, conn: psycopg.Connection, set_id: str, questions: list[dict]) -> None:
        seen_keys: set[str] = set()
        for index, question in enumerate(questions, start=1):
            case_key = question["case_key"]
            if case_key in seen_keys:
                raise ValueError(f"Duplicate case_key in question set: {case_key}")
            seen_keys.add(case_key)
            conn.execute(
                """
                INSERT INTO benchmark_questions (
                    id, set_id, case_key, position, question, tags, reference_answer, exact_answer,
                    required_terms, required_any, forbidden_terms, required_sources,
                    expected_refusal, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    question.get("id") or str(uuid4()),
                    set_id,
                    case_key,
                    index,
                    question["question"],
                    Jsonb(question.get("tags", [])),
                    question.get("reference_answer"),
                    question.get("exact_answer"),
                    Jsonb(question.get("required_terms", [])),
                    Jsonb(question.get("required_any", [])),
                    Jsonb(question.get("forbidden_terms", [])),
                    Jsonb(question.get("required_sources", [])),
                    bool(question.get("expected_refusal", False)),
                    question.get("notes"),
                ),
            )

    @staticmethod
    def _normalize_questions(questions: list[dict]) -> list[dict]:
        normalized: list[dict] = []
        for index, item in enumerate(questions, start=1):
            question_text = str(item.get("question", "")).strip()
            case_key = str(item.get("case_key") or item.get("id") or f"case-{index}").strip()
            if not question_text:
                raise ValueError(f"Question #{index} is empty")
            if not case_key:
                raise ValueError(f"Question #{index} has empty case_key")
            normalized.append(
                {
                    "id": item.get("id"),
                    "case_key": case_key,
                    "question": question_text,
                    "tags": list(item.get("tags", [])),
                    "reference_answer": item.get("reference_answer"),
                    "exact_answer": item.get("exact_answer"),
                    "required_terms": list(item.get("required_terms", [])),
                    "required_any": list(item.get("required_any", [])),
                    "forbidden_terms": list(item.get("forbidden_terms", [])),
                    "required_sources": list(item.get("required_sources", [])),
                    "expected_refusal": bool(item.get("expected_refusal", False)),
                    "notes": item.get("notes"),
                }
            )
        return normalized

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._settings.benchmark_database_url, row_factory=dict_row)
