from __future__ import annotations

from app.domain.models import Citation, QueryAnalysis, RetrievedChunk
from app.prompts.templates import ANSWER_SYSTEM_PROMPT
from app.providers.openrouter import OpenRouterProvider


class GenerationService:
    def __init__(self, provider: OpenRouterProvider) -> None:
        self._provider = provider

    def generate(self, analysis: QueryAnalysis, chunks: list[RetrievedChunk]) -> tuple[str, list[Citation]]:
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
            return _build_fallback_answer(analysis, chunks), citations

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

        context_text = "\n\n".join(context_blocks)
        prompt = (
            f"Запрос пользователя: {analysis.original_query}\n"
            f"Переписанный запрос: {analysis.rewritten_query}\n"
            f"Фильтры: {analysis.filters}\n\n"
            f"Контекст:\n\n{context_text}"
        )
        answer = self._provider.complete(
            system_prompt=ANSWER_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.0,
        )
        return answer, citations


def _build_fallback_answer(analysis: QueryAnalysis, chunks: list[RetrievedChunk]) -> str:
    lines = [
        f"Переписанный запрос: {analysis.rewritten_query}",
        "",
        "Ниже собран релевантный контекст без генерации через OpenRouter, потому что провайдер не настроен.",
        "",
    ]
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
