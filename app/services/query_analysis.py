from __future__ import annotations

import json

from app.domain.models import QueryAnalysis
from app.prompts.templates import QUERY_ANALYSIS_SYSTEM_PROMPT
from app.providers.openrouter import OpenRouterProvider
from app.services.ner import augment_query_with_entities, extract_named_entities, merge_named_entities
from app.services.text_utils import unique_preserve


QUERY_MODE_VALUES = {"classic", "graph_first", "mixed"}
ROUTER_ACCEPT_THRESHOLD = 0.75
ROUTER_MIXED_THRESHOLD = 0.6

PKCS11_INTENT_SYMBOLS = {
    "C_CreateObject": (
        "создания объекта",
        "создать объект",
        "создания объектов",
        "создает объект",
    ),
    "C_DestroyObject": (
        "удаления объекта",
        "удалить объект",
        "удаляет объект",
        "уничтожения объекта",
    ),
    "C_SignInit": (
        "инициализации операции подписи",
        "инициализирует операцию подписи",
        "инициализации подписи",
        "подготовки подписи",
    ),
    "C_Sign": (
        "создание подписи после инициализации",
        "выполняет создание подписи",
        "создает подпись",
        "сформировать подпись",
        "выполняет подпись",
    ),
    "C_VerifyInit": (
        "инициализации операции проверки",
        "инициализирует операцию проверки",
        "инициализации проверки подписи",
        "подготовки проверки подписи",
    ),
    "C_Verify": (
        "саму проверку подписи",
        "проверки подписи",
        "выполняет проверку подписи",
        "проверяет подпись",
    ),
    "C_GenerateKeyPair": (
        "генерации пары ключей",
        "сгенерировать пару ключей",
        "генерирует пару ключей",
        "пары ключей",
    ),
    "C_DeriveKey": (
        "производного получения ключа",
        "производный ключ",
        "derive key",
        "получения производного ключа",
    ),
}

REFERENCE_SECTION_TERMS = (
    "Синтаксис",
    "Параметры",
    "Назначение",
    "Примечание",
    "Возвращаемые значения",
    "Пример",
)

GRAPH_FIRST_MARKERS = (
    "архитектур",
    "интеграц",
    "связ",
    "взаимодейств",
    "компонент",
    "инфраструктур",
    "совместим",
    "поддержива",
    "какие ос",
    "какие интерфейсы",
    "какие продукты",
    "какие варианты",
    "чем отличаются",
    "сравн",
    "завис",
    "требован",
    "что нужно для",
    "что требуется для",
)

EXACT_MATCH_MARKERS = (
    "функц",
    "вызов",
    "код ошибки",
    "ошибка",
    "пример команды",
    "команда",
    "--",
    "синтаксис",
    "параметр",
    "возвращаем",
)

ROUTING_MARKERS = (
    "где опис",
    "в какой инструкции",
    "на какой странице",
    "в каком разделе",
    "где в документации",
)

FACTOID_MARKERS = (
    "какой порт",
    "какая версия",
    "какой скрипт",
    "какой файл",
    "какая утилита",
    "какая команда",
    "какой компонент",
    "какое имя",
)


class QueryAnalysisService:
    def __init__(self, provider: OpenRouterProvider) -> None:
        self._provider = provider

    def analyze(self, query: str) -> QueryAnalysis:
        extracted_entities = _enrich_entities(query, extract_named_entities(query))
        forced_mode = _forced_query_mode(query, extracted_entities)
        if forced_mode is not None:
            return _build_analysis(
                query=query,
                rewritten_query=_rewrite_with_pkcs11_hints(query, extracted_entities, query),
                filters=_merge_filters({}, extracted_entities),
                entities=extracted_entities,
                intent=_forced_intent(query, forced_mode),
                needs_code=_needs_code(query),
                query_mode=forced_mode,
                routing_confidence=1.0,
                routing_reason=f"forced_{forced_mode}",
            )

        if self._provider.is_configured():
            routed = self._route_with_llm(query, extracted_entities)
            if routed is not None:
                return routed

        return self._heuristic(query)

    def _route_with_llm(self, query: str, entities: dict[str, list[str]]) -> QueryAnalysis | None:
        try:
            payload = self._provider.complete_json(
                system_prompt=QUERY_ANALYSIS_SYSTEM_PROMPT,
                user_prompt=(
                    f"User query:\n{query}\n\n"
                    f"Extracted entities:\n{json.dumps(entities, ensure_ascii=False)}"
                ),
            )
        except Exception:
            return None

        rewritten_query = _rewrite_with_pkcs11_hints(
            str(payload.get("rewritten_query") or query),
            entities,
            query,
        )
        filters = _merge_filters(payload.get("filters", {}), entities)
        intent = str(payload.get("intent") or "general").strip() or "general"
        needs_code = bool(payload.get("needs_code", False))
        router_mode = _normalize_query_mode(payload.get("query_mode"))
        confidence = _normalize_confidence(payload.get("confidence"))
        reason = str(payload.get("reason") or "").strip() or None

        query_mode = _resolve_llm_query_mode(
            original_query=query,
            rewritten_query=rewritten_query,
            entities=entities,
            router_mode=router_mode,
            confidence=confidence,
        )

        return _build_analysis(
            query=query,
            rewritten_query=rewritten_query,
            filters=filters,
            entities=entities,
            intent=intent,
            needs_code=needs_code,
            query_mode=query_mode,
            routing_confidence=confidence,
            routing_reason=reason,
        )

    def _heuristic(self, query: str) -> QueryAnalysis:
        entities = _enrich_entities(query, extract_named_entities(query))
        rewritten = _rewrite_with_pkcs11_hints(query, entities, query)
        return _build_analysis(
            query=query,
            rewritten_query=rewritten,
            filters=_merge_filters({}, entities),
            entities=entities,
            intent="general",
            needs_code=_needs_code(query),
            query_mode=_fallback_query_mode(query, rewritten, entities),
            routing_confidence=None,
            routing_reason="heuristic_fallback",
        )


def _build_analysis(
    *,
    query: str,
    rewritten_query: str,
    filters: dict[str, list[str] | str],
    entities: dict[str, list[str]],
    intent: str,
    needs_code: bool,
    query_mode: str,
    routing_confidence: float | None,
    routing_reason: str | None,
) -> QueryAnalysis:
    return QueryAnalysis(
        original_query=query,
        rewritten_query=rewritten_query,
        filters=filters,
        entities=entities,
        intent=intent,
        needs_code=needs_code,
        query_mode=query_mode,
        routing_confidence=routing_confidence,
        routing_reason=routing_reason,
    )


def _normalize_filter_keys(filters: dict) -> dict[str, list[str] | str]:
    allowed = {"language_tags", "os_tags", "interfaces", "products", "components", "api_symbols"}
    result: dict[str, list[str] | str] = {}
    for key, value in filters.items():
        if key not in allowed:
            continue
        if isinstance(value, list):
            result[key] = [str(item) for item in value if item]
        elif value:
            result[key] = str(value)
    return result


def _merge_filters(
    raw_filters: dict,
    extracted_entities: dict[str, list[str]],
) -> dict[str, list[str] | str]:
    normalized = _normalize_filter_keys(raw_filters)
    extracted_filters = {
        key: value
        for key, value in extracted_entities.items()
        if key in {"language_tags", "os_tags", "interfaces", "products", "components", "api_symbols"}
    }
    merged = merge_named_entities(
        {key: value for key, value in normalized.items() if isinstance(value, list)},
        extracted_filters,
    )
    return {key: value for key, value in merged.items() if value}


def _enrich_entities(query: str, entities: dict[str, list[str]]) -> dict[str, list[str]]:
    query_lower = query.lower()
    inferred_symbols = _infer_pkcs11_symbols(query_lower)
    merged = merge_named_entities(
        entities,
        {
            "api_symbols": inferred_symbols,
            "interfaces": ["pkcs11"] if inferred_symbols else [],
        },
    )
    return merged


def _infer_pkcs11_symbols(query_lower: str) -> list[str]:
    inferred: list[str] = []
    for symbol, phrases in PKCS11_INTENT_SYMBOLS.items():
        if any(phrase in query_lower for phrase in phrases):
            inferred.append(symbol)
    return unique_preserve(inferred)


def _rewrite_with_pkcs11_hints(
    rewritten_query: str,
    entities: dict[str, list[str]],
    original_query: str,
) -> str:
    rewritten = augment_query_with_entities(rewritten_query, entities)
    query_lower = original_query.lower()
    additions: list[str] = []

    if entities.get("api_symbols"):
        additions.extend(f"{symbol}()" for symbol in entities["api_symbols"])

    if (
        "pkcs11" in entities.get("interfaces", [])
        and (
            "какие разделы" in query_lower
            or "описание функции" in query_lower
            or "какие секции" in query_lower
        )
    ):
        additions.extend(REFERENCE_SECTION_TERMS)
        additions.append("reference")

    additions = [term for term in unique_preserve(additions) if term not in rewritten]
    if not additions:
        return rewritten
    return f"{rewritten} {' '.join(additions)}"


def _forced_query_mode(query: str, entities: dict[str, list[str]]) -> str | None:
    if _looks_exact_query(query, entities):
        return "classic"
    if _looks_routing_query(query):
        return "classic"
    if _looks_factoid_query(query):
        return "classic"
    return None


def _forced_intent(query: str, forced_mode: str) -> str:
    if forced_mode != "classic":
        return "general"
    if _looks_routing_query(query):
        return "routing"
    if _looks_factoid_query(query):
        return "factoid"
    if "pkcs11" in query.lower():
        return "api_reference"
    return "general"


def _resolve_llm_query_mode(
    *,
    original_query: str,
    rewritten_query: str,
    entities: dict[str, list[str]],
    router_mode: str | None,
    confidence: float,
) -> str:
    forced = _forced_query_mode(original_query, entities)
    if forced is not None:
        return forced

    if router_mode == "classic":
        return "classic"

    if router_mode == "mixed":
        if confidence >= ROUTER_ACCEPT_THRESHOLD and _looks_mixed_query(original_query, rewritten_query, entities):
            return "mixed"
        if confidence >= ROUTER_MIXED_THRESHOLD and _looks_relation_query(original_query, rewritten_query, entities):
            return "mixed"
        return "classic"

    if router_mode == "graph_first":
        if confidence >= ROUTER_ACCEPT_THRESHOLD and _looks_relation_query(original_query, rewritten_query, entities):
            return "graph_first"
        return "classic"

    return _fallback_query_mode(original_query, rewritten_query, entities)


def _fallback_query_mode(
    original_query: str,
    rewritten_query: str,
    entities: dict[str, list[str]],
) -> str:
    if _looks_mixed_query(original_query, rewritten_query, entities):
        return "mixed"
    if _looks_relation_query(original_query, rewritten_query, entities):
        return "graph_first"
    return "classic"


def _looks_exact_query(query: str, entities: dict[str, list[str]]) -> bool:
    query_lower = query.lower()
    if entities.get("api_symbols"):
        return True
    if "pkcs11" in entities.get("interfaces", []) and any(marker in query_lower for marker in EXACT_MATCH_MARKERS):
        return True
    return "ckr_" in query_lower or "c_" in query_lower or "--" in query_lower


def _looks_routing_query(query: str) -> bool:
    query_lower = query.lower()
    return any(marker in query_lower for marker in ROUTING_MARKERS)


def _looks_factoid_query(query: str) -> bool:
    query_lower = query.lower()
    return any(marker in query_lower for marker in FACTOID_MARKERS)


def _looks_relation_query(
    original_query: str,
    rewritten_query: str,
    entities: dict[str, list[str]],
) -> bool:
    query_lower = f"{original_query} {rewritten_query}".lower()
    relation_signal = any(marker in query_lower for marker in GRAPH_FIRST_MARKERS)
    major_entity_groups = sum(1 for key in ("products", "interfaces", "components", "os_tags") if entities.get(key))
    total_major_entities = sum(len(entities.get(key, [])) for key in ("products", "interfaces", "components", "os_tags"))
    if relation_signal and major_entity_groups >= 1 and total_major_entities >= 2:
        return True
    return False


def _looks_mixed_query(
    original_query: str,
    rewritten_query: str,
    entities: dict[str, list[str]],
) -> bool:
    return _looks_exact_query(original_query, entities) and _looks_relation_query(original_query, rewritten_query, entities)


def _normalize_query_mode(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in QUERY_MODE_VALUES:
        return normalized
    return None


def _normalize_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _needs_code(query: str) -> bool:
    query_lower = query.lower()
    return any(token in query_lower for token in ["пример", "код", "python", "c#", "java", "как сделать"])
