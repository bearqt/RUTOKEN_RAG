from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.api.schemas import (
    BenchmarkQuestionSetInput,
    BenchmarkQuestionSetResponse,
    BenchmarkQuestionSetSummaryResponse,
    BenchmarkRunSummaryResponse,
    CitationResponse,
    HealthResponse,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    RetrievalMode,
    RetrievedChunkResponse,
)
from app.config import settings
from app.providers.gigachat import GigaChatEmbeddingsProvider, ProviderConfigurationError
from app.providers.openrouter import OpenRouterProvider
from app.services.bm25_baseline import BM25BaselineService
from app.services.benchmarking import BenchmarkService
from app.services.bootstrap import bootstrap_if_needed
from app.services.generation import GenerationService
from app.services.graph_index import GraphIndexService
from app.services.ingestion import IngestionService
from app.services.pipeline import RagPipelineService
from app.services.query_analysis import QueryAnalysisService
from app.services.search import HybridSearchService

BENCHMARK_PAGE = Path(__file__).resolve().parent / "web" / "benchmark.html"
RAG_PIPELINE_PAGE = Path(__file__).resolve().parent / "web" / "rag_pipeline.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap_if_needed(settings)
    graph_index = GraphIndexService(settings)
    graph_index.ensure_from_storage()
    openrouter = OpenRouterProvider(settings)
    query_analysis = QueryAnalysisService(openrouter)
    search = HybridSearchService(settings)
    generation = GenerationService(openrouter)
    app.state.graph_index = graph_index
    app.state.query_analysis = query_analysis
    app.state.search = search
    app.state.generation = generation
    app.state.bm25_baseline = BM25BaselineService(settings)
    app.state.ingestion = IngestionService(settings)
    app.state.pipeline = RagPipelineService(query_analysis, search, generation)
    app.state.benchmark = BenchmarkService(settings, app.state.pipeline)
    app.state.benchmark.initialize()
    app.state.benchmark_baseline = BenchmarkService(settings, app.state.bm25_baseline)
    app.state.benchmark_baseline.initialize()
    yield


app = FastAPI(title="Rutoken RAG", version="0.1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        chunks_indexed=settings.chunks_path.exists(),
        manifest_exists=settings.manifest_path.exists(),
        openrouter_configured=OpenRouterProvider(settings).is_configured(),
        gigachat_configured=GigaChatEmbeddingsProvider(settings).is_configured(),
    )


@app.post("/ingest", response_model=IngestResponse)
def ingest() -> IngestResponse:
    try:
        result = app.state.ingestion.ingest()
    except ProviderConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    app.state.search.refresh()
    app.state.bm25_baseline.refresh()
    return IngestResponse(documents=result.documents, chunks=result.chunks, vector_size=result.vector_size)


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        if request.retrieval_mode == "bm25_baseline":
            result = app.state.bm25_baseline.run(request.question, retrieval_mode=request.retrieval_mode)
        else:
            result = app.state.pipeline.run(request.question, retrieval_mode=request.retrieval_mode)
    except ProviderConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=f"Index is missing: {error}") from error

    return QueryResponse(
        original_query=result.analysis.original_query,
        rewritten_query=result.analysis.rewritten_query,
        filters=result.analysis.filters,
        query_mode=result.analysis.query_mode,
        retrieval_mode=result.retrieval_mode,
        routing_confidence=result.analysis.routing_confidence,
        routing_reason=result.analysis.routing_reason,
        answer=result.answer,
        graph_facts=result.graph_facts,
        citations=[
            CitationResponse(
                source_url=item.source_url,
                title=item.title,
                heading_path=item.heading_path,
                chunk_id=item.chunk_id,
            )
            for item in result.citations
        ],
        retrieved_chunks=[
            RetrievedChunkResponse(
                chunk_id=item.chunk.chunk_id,
                title=item.chunk.title,
                heading_path=item.chunk.heading_path,
                source_url=item.chunk.source_url,
                chunk_type=item.chunk.chunk_type,
                dense_score=item.dense_score,
                sparse_score=item.sparse_score,
                graph_score=item.graph_score,
                fused_score=item.fused_score,
                rerank_score=item.rerank_score,
                text=item.chunk.text,
            )
            for item in result.retrieved_chunks
        ],
    )


@app.get("/benchmark", response_class=HTMLResponse, include_in_schema=False)
def benchmark_page() -> HTMLResponse:
    if not BENCHMARK_PAGE.exists():
        raise HTTPException(status_code=404, detail="Benchmark page is missing")
    return HTMLResponse(BENCHMARK_PAGE.read_text(encoding="utf-8"))


@app.get("/rag-pipeline", response_class=HTMLResponse, include_in_schema=False)
def rag_pipeline_page() -> HTMLResponse:
    if not RAG_PIPELINE_PAGE.exists():
        raise HTTPException(status_code=404, detail="RAG pipeline page is missing")
    return HTMLResponse(RAG_PIPELINE_PAGE.read_text(encoding="utf-8"))


@app.get("/benchmark/sets", response_model=list[BenchmarkQuestionSetSummaryResponse])
def benchmark_sets() -> list[BenchmarkQuestionSetSummaryResponse]:
    return [
        BenchmarkQuestionSetSummaryResponse(**item)
        for item in app.state.benchmark.list_question_sets()
    ]


@app.post("/benchmark/sets", response_model=BenchmarkQuestionSetResponse)
def benchmark_create_set(request: BenchmarkQuestionSetInput) -> BenchmarkQuestionSetResponse:
    try:
        created = app.state.benchmark.create_question_set(request.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return BenchmarkQuestionSetResponse(**created)


@app.get("/benchmark/sets/{set_id}", response_model=BenchmarkQuestionSetResponse)
def benchmark_get_set(set_id: str) -> BenchmarkQuestionSetResponse:
    payload = app.state.benchmark.get_question_set(set_id)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Question set not found: {set_id}")
    return BenchmarkQuestionSetResponse(**payload)


@app.put("/benchmark/sets/{set_id}", response_model=BenchmarkQuestionSetResponse)
def benchmark_update_set(set_id: str, request: BenchmarkQuestionSetInput) -> BenchmarkQuestionSetResponse:
    try:
        updated = app.state.benchmark.update_question_set(set_id, request.model_dump())
    except ProviderConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Question set not found: {set_id}")
    return BenchmarkQuestionSetResponse(**updated)


@app.post("/benchmark/sets/{set_id}/run")
def benchmark_run(
    set_id: str,
    retrieval_mode: RetrievalMode = Query(default="hybrid"),
) -> dict:
    try:
        benchmark_service = (
            app.state.benchmark_baseline
            if retrieval_mode == "bm25_baseline"
            else app.state.benchmark
        )
        run = benchmark_service.run(set_id, retrieval_mode=retrieval_mode)
    except ProviderConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return run


@app.get("/benchmark/runs", response_model=list[BenchmarkRunSummaryResponse])
def benchmark_runs(
    set_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[BenchmarkRunSummaryResponse]:
    return [
        BenchmarkRunSummaryResponse(**item)
        for item in app.state.benchmark.list_runs(set_id=set_id, limit=limit)
    ]


@app.get("/benchmark/runs/{run_id}")
def benchmark_run_detail(run_id: str) -> dict:
    payload = app.state.benchmark.get_run(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Benchmark run not found: {run_id}")
    return payload


@app.get("/benchmark/results")
def benchmark_latest_result(set_id: str | None = None) -> dict:
    runs = app.state.benchmark.list_runs(set_id=set_id, limit=1)
    if not runs:
        return {"run": None}
    payload = app.state.benchmark.get_run(runs[0]["id"])
    return {"run": payload}
