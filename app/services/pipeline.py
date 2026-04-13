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

    def run(self, question: str, retrieval_mode: str = "hybrid") -> PipelineResult:
        analysis = self._query_analysis.analyze(question)
        search_result = self._search.search(
            analysis.rewritten_query,
            analysis.filters,
            analysis.entities,
            analysis.query_mode,
            retrieval_mode,
        )
        answer, citations = self._generation.generate(analysis, search_result.chunks, search_result.graph_facts)
        return PipelineResult(
            analysis=analysis,
            answer=answer,
            citations=citations,
            retrieved_chunks=search_result.chunks,
            ranked_chunks=search_result.ranked_chunks,
            retrieval_mode=search_result.retrieval_mode,
            graph_facts=search_result.graph_facts,
        )
