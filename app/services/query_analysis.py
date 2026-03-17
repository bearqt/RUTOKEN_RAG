from __future__ import annotations

import json

from app.domain.models import QueryAnalysis
from app.prompts.templates import QUERY_ANALYSIS_SYSTEM_PROMPT
from app.providers.openrouter import OpenRouterProvider
from app.services.enrichment import INTERFACES, LANGUAGE_HINTS, OPERATING_SYSTEMS, PRODUCTS
from app.services.text_utils import extract_symbols


class QueryAnalysisService:
    def __init__(self, provider: OpenRouterProvider) -> None:
        self._provider = provider

    def analyze(self, query: str) -> QueryAnalysis:
        if self._provider.is_configured():
            try:
                payload = self._provider.complete_json(
                    system_prompt=QUERY_ANALYSIS_SYSTEM_PROMPT,
                    user_prompt=f"Запрос пользователя:\n{query}",
                )
                return QueryAnalysis(
                    original_query=query,
                    rewritten_query=payload.get("rewritten_query", query),
                    filters=_normalize_filter_keys(payload.get("filters", {})),
                    intent=payload.get("intent", "general"),
                    needs_code=bool(payload.get("needs_code", False)),
                )
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                pass
        return self._heuristic(query)

    def _heuristic(self, query: str) -> QueryAnalysis:
        query_lower = query.lower()
        filters = {
            "language_tags": [tag for label, tag in LANGUAGE_HINTS.items() if label in query_lower],
            "os_tags": [tag for label, tag in OPERATING_SYSTEMS.items() if label in query_lower],
            "interfaces": [tag for label, tag in INTERFACES.items() if label in query_lower],
            "products": [tag for label, tag in PRODUCTS.items() if label in query_lower],
            "api_symbols": extract_symbols(query),
        }
        filters = {key: value for key, value in filters.items() if value}
        rewritten = query
        if filters.get("api_symbols"):
            rewritten = f"{query} {' '.join(filters['api_symbols'])}"
        return QueryAnalysis(
            original_query=query,
            rewritten_query=rewritten,
            filters=filters,
            intent="general",
            needs_code=any(token in query_lower for token in ["пример", "код", "python", "c#", "java", "как сделать"]),
        )


def _normalize_filter_keys(filters: dict) -> dict[str, list[str] | str]:
    allowed = {"language_tags", "os_tags", "interfaces", "products", "api_symbols"}
    result: dict[str, list[str] | str] = {}
    for key, value in filters.items():
        if key not in allowed:
            continue
        if isinstance(value, list):
            result[key] = [str(item) for item in value if item]
        elif value:
            result[key] = str(value)
    return result

