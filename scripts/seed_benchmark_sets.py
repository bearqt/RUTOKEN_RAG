from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.services.benchmark_repository import BenchmarkRepository
from app.services.benchmark_seed_data import get_seed_question_sets


def main() -> None:
    repository = BenchmarkRepository(settings)
    repository.ensure_schema()
    repository.ensure_seed_sets(get_seed_question_sets())

    print("Seed question sets:")
    for payload in get_seed_question_sets():
        stored = repository.get_question_set(payload["id"])
        question_count = len(stored["questions"]) if stored else 0
        print(f"- {payload['id']}: {question_count} questions")


if __name__ == "__main__":
    main()
