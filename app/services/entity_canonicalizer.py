from __future__ import annotations

from app.services.ner import ENTITY_FIELDS, canonicalize_entity_value, merge_named_entities
from app.services.text_utils import unique_preserve


ALLOWED_RELATION_PREDICATES = {
    "supports_interface",
    "available_on_os",
    "uses_component",
    "belongs_to_interface",
    "returns_error_code",
    "uses_pkcs11_object",
    "uses_mechanism",
    "compatible_with",
}

RELATION_ALIASES = {
    "supports": "supports_interface",
    "support": "supports_interface",
    "supports_interface": "supports_interface",
    "available_on": "available_on_os",
    "available_on_os": "available_on_os",
    "runs_on": "available_on_os",
    "uses_component": "uses_component",
    "uses": "uses_component",
    "belongs_to_interface": "belongs_to_interface",
    "belongs_to": "belongs_to_interface",
    "returns_error": "returns_error_code",
    "returns_error_code": "returns_error_code",
    "uses_object": "uses_pkcs11_object",
    "uses_pkcs11_object": "uses_pkcs11_object",
    "uses_mechanism": "uses_mechanism",
    "compatible_with": "compatible_with",
}

SYMMETRIC_RELATIONS = {"compatible_with"}


class EntityCanonicalizer:
    def canonicalize_entities(self, entities: dict | None) -> dict[str, list[str]]:
        if not isinstance(entities, dict):
            return {}

        normalized: dict[str, list[str]] = {}
        for entity_type, values in entities.items():
            if entity_type not in ENTITY_FIELDS or not isinstance(values, list):
                continue
            canonical_values = [
                canonical
                for value in values
                if (canonical := canonicalize_entity_value(entity_type, str(value))) is not None
            ]
            if canonical_values:
                normalized[entity_type] = unique_preserve(canonical_values)
        return normalized

    def merge_entities(
        self,
        rule_entities: dict[str, list[str]] | None,
        llm_entities: dict[str, list[str]] | None,
    ) -> dict[str, list[str]]:
        return merge_named_entities(rule_entities or {}, llm_entities or {})

    def canonicalize_relations(
        self,
        relations: list[dict] | None,
        known_entities: dict[str, list[str]] | None = None,
        confidence_threshold: float = 0.0,
    ) -> list[dict[str, str | float]]:
        if not isinstance(relations, list):
            return []

        known_entities = known_entities or {}
        normalized: list[dict[str, str | float]] = []
        seen: set[tuple[str, str, str]] = set()
        for relation in relations:
            if not isinstance(relation, dict):
                continue

            predicate = RELATION_ALIASES.get(str(relation.get("predicate") or "").strip().lower())
            if predicate not in ALLOWED_RELATION_PREDICATES:
                continue

            src_type = str(relation.get("src_type") or "").strip()
            tgt_type = str(relation.get("tgt_type") or "").strip()
            if src_type not in ENTITY_FIELDS or tgt_type not in ENTITY_FIELDS:
                continue

            src_value = canonicalize_entity_value(src_type, _safe_text(relation.get("src_value")))
            tgt_value = canonicalize_entity_value(tgt_type, _safe_text(relation.get("tgt_value")))
            if src_value is None or tgt_value is None:
                continue

            confidence = _safe_confidence(relation.get("confidence"))
            if confidence < confidence_threshold:
                continue

            if known_entities and src_value not in known_entities.get(src_type, []) and tgt_value not in known_entities.get(tgt_type, []):
                # Allow relation-only discoveries only when at least one endpoint is known.
                continue

            if predicate in SYMMETRIC_RELATIONS and (tgt_type, tgt_value) < (src_type, src_value):
                src_type, tgt_type = tgt_type, src_type
                src_value, tgt_value = tgt_value, src_value

            key = (f"{src_type}:{src_value}", predicate, f"{tgt_type}:{tgt_value}")
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                {
                    "src_type": src_type,
                    "src_value": src_value,
                    "predicate": predicate,
                    "tgt_type": tgt_type,
                    "tgt_value": tgt_value,
                    "confidence": confidence,
                    "evidence": _safe_text(relation.get("evidence")),
                    "source": "llm",
                }
            )
        return normalized


def _safe_confidence(value: object) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, numeric))


def _safe_text(value: object) -> str:
    return str(value).strip() if value is not None else ""
