from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from app.api.schemas import CitationResponse, HealthResponse, IngestResponse, QueryRequest, QueryResponse, RetrievedChunkResponse
from app.config import settings
from app.providers.gigachat import GigaChatEmbeddingsProvider, ProviderConfigurationError
from app.providers.openrouter import OpenRouterProvider
from app.services.benchmarking import BenchmarkService
from app.services.bootstrap import bootstrap_if_needed
from app.services.generation import GenerationService
from app.services.ingestion import IngestionService
from app.services.pipeline import RagPipelineService
from app.services.query_analysis import QueryAnalysisService
from app.services.search import HybridSearchService

BENCHMARK_PAGE = Path(__file__).resolve().parent / "web" / "benchmark.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap_if_needed(settings)
    openrouter = OpenRouterProvider(settings)
    query_analysis = QueryAnalysisService(openrouter)
    search = HybridSearchService(settings)
    generation = GenerationService(openrouter)
    app.state.query_analysis = query_analysis
    app.state.search = search
    app.state.generation = generation
    app.state.ingestion = IngestionService(settings)
    app.state.pipeline = RagPipelineService(query_analysis, search, generation)
    app.state.benchmark = BenchmarkService(settings, app.state.pipeline)
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
    return IngestResponse(documents=result.documents, chunks=result.chunks, vector_size=result.vector_size)


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        result = app.state.pipeline.run(request.question)
    except ProviderConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=f"Index is missing: {error}") from error

    return QueryResponse(
        original_query=result.analysis.original_query,
        rewritten_query=result.analysis.rewritten_query,
        filters=result.analysis.filters,
        answer=result.answer,
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


@app.get("/benchmark/cases")
def benchmark_cases() -> dict:
    try:
        cases = app.state.benchmark.preview_cases()
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"dataset_path": str(settings.benchmark_dataset_path), "cases": cases}


@app.get("/benchmark/results")
def benchmark_results() -> dict:
    payload = app.state.benchmark.load_last_run()
    if payload is None:
        return {"dataset_path": str(settings.benchmark_dataset_path), "summary": None, "cases": []}
    return payload


@app.post("/benchmark/run")
def benchmark_run() -> dict:
    try:
        run = app.state.benchmark.run()
    except ProviderConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return run.to_record()
