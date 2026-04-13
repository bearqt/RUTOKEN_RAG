from __future__ import annotations

from app.domain.models import Citation, QueryAnalysis, RetrievedChunk
from app.prompts.templates import ANSWER_SYSTEM_PROMPT
from app.providers.openrouter import OpenRouterProvider


class GenerationService:
    def __init__(self, provider: OpenRouterProvider) -> None:
        self._provider = provider

    def generate(
        self,
        analysis: QueryAnalysis,
        chunks: list[RetrievedChunk],
        graph_facts: list[str] | None = None,
    ) -> tuple[str, list[Citation]]:
        graph_facts = graph_facts or []
        citations = [
            Citation(
                source_url=item.chunk.source_url,
                title=item.chunk.title,
                heading_path=item.chunk.heading_path,
                chunk_id=item.chunk.chunk_id,
            )
            for item in chunks
        ]
        if not chunks:
            return "В доступном контексте нет данных, достаточных для точного ответа.", citations

        if not self._provider.is_configured():
            return _build_fallback_answer(analysis, chunks, graph_facts), citations

        context_blocks = []
        for index, item in enumerate(chunks, start=1):
            context_blocks.append(
                "\n".join(
                    [
                        f"[Источник {index}]",
                        f"URL: {item.chunk.source_url}",
                        f"Заголовок: {item.chunk.title}",
                        f"Раздел: {' > '.join(item.chunk.heading_path)}",
                        item.chunk.text,
                    ]
                )
            )

        graph_section = ""
        if graph_facts:
            graph_section = "Graph facts:\n" + "\n".join(f"- {fact}" for fact in graph_facts) + "\n\n"

        context_text = "\n\n".join(context_blocks)
        prompt = (
            f"Запрос пользователя: {analysis.original_query}\n"
            f"Переписанный запрос: {analysis.rewritten_query}\n"
            f"Режим поиска: {analysis.query_mode}\n"
            f"Фильтры: {analysis.filters}\n\n"
            f"{graph_section}"
            f"Контекст:\n\n{context_text}"
        )
        try:
            answer = self._provider.complete(
                system_prompt=ANSWER_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.0,
            )
            return answer, citations
        except Exception:
            return _build_fallback_answer(analysis, chunks, graph_facts), citations


def _build_fallback_answer(
    analysis: QueryAnalysis,
    chunks: list[RetrievedChunk],
    graph_facts: list[str],
) -> str:
    lines = [
        f"Переписанный запрос: {analysis.rewritten_query}",
        f"Режим поиска: {analysis.query_mode}",
        "",
    ]
    if graph_facts:
        lines.append("Graph facts:")
        lines.extend(f"- {fact}" for fact in graph_facts)
        lines.append("")
    lines.extend(
        [
            "Ниже собран релевантный контекст без генерации через OpenRouter, потому что провайдер не настроен.",
            "",
        ]
    )
    for index, item in enumerate(chunks, start=1):
        lines.extend(
            [
                f"{index}. {item.chunk.title} / {' > '.join(item.chunk.heading_path)}",
                item.chunk.text[:1200].strip(),
                f"Источник: {item.chunk.source_url}",
                "",
            ]
        )
    return "\n".join(lines).strip()
