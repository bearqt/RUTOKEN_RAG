from __future__ import annotations

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
    bootstrap_if_needed(settings)
    openrouter = OpenRouterProvider(settings)
    pipeline = RagPipelineService(
        QueryAnalysisService(openrouter),
        HybridSearchService(settings),
        GenerationService(openrouter),
    )
    benchmark = BenchmarkService(settings, pipeline)
    result = benchmark.run()
    print(json.dumps(result.to_record(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
