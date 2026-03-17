from __future__ import annotations

from app.domain.models import PipelineResult
from app.services.generation import GenerationService
from app.services.query_analysis import QueryAnalysisService
from app.services.search import HybridSearchService


class RagPipelineService:
    def __init__(
        self,
        query_analysis: QueryAnalysisService,
        search: HybridSearchService,
        generation: GenerationService,
    ) -> None:
        self._query_analysis = query_analysis
        self._search = search
        self._generation = generation

    def run(self, question: str) -> PipelineResult:
        analysis = self._query_analysis.analyze(question)
        chunks = self._search.search(analysis.rewritten_query, analysis.filters)
        answer, citations = self._generation.generate(analysis, chunks)
        return PipelineResult(
            analysis=analysis,
            answer=answer,
            citations=citations,
            retrieved_chunks=chunks,
        )
