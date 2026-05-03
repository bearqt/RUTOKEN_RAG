from __future__ import annotations

import argparse
import json

from app.config import settings
from app.providers.openrouter import OpenRouterProvider
from app.services.benchmarking import BenchmarkService
from app.services.bootstrap import bootstrap_if_needed
from app.services.generation import GenerationService
from app.services.pipeline import RagPipelineService
from app.services.query_analysis import QueryAnalysisService
from app.services.search import HybridSearchService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set-id", dest="set_id")
    args = parser.parse_args()

    bootstrap_if_needed(settings)
    openrouter = OpenRouterProvider(settings)
    pipeline = RagPipelineService(
        QueryAnalysisService(openrouter),
        HybridSearchService(settings),
        GenerationService(openrouter),
    )
    benchmark = BenchmarkService(settings, pipeline)
    benchmark.initialize()
    set_id = args.set_id
    if not set_id:
        sets = benchmark.list_question_sets()
        if not sets:
            raise RuntimeError("No benchmark question sets found")
        set_id = sets[0]["id"]
    result = benchmark.run(set_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
