from __future__ import annotations

from typing import Any

from app.domain.models import Chunk, SourceDocument
from app.services.ner import entity_terms, extract_named_entities, merge_named_entities
from app.services.text_utils import unique_preserve


GRAPH_METADATA_VERSION = 1


def classify_doc_family(document: SourceDocument) -> str:
    title = document.title.lower()
    if "Р°СЂС…РёС‚РµРєС‚СѓСЂР°" in title:
        return "architecture"
    if "РѕР±Р·РѕСЂРЅР°СЏ РёРЅС„РѕСЂРјР°С†РёСЏ" in title or "СЃСЂР°РІРЅРµРЅРёРµ С‚РµС…РЅРёС‡РµСЃРєРёС… С…Р°СЂР°РєС‚РµСЂРёСЃС‚РёРє" in title:
        return "product_matrix"
    if "РѕР±СЉРµРєС‚" in title and "pkcs" in title:
        return "pkcs11_objects"
    if "С…СЂР°РЅРёР»РёС‰" in title:
        return "storage"
    if "РІС‹Р±РѕСЂ" in title or "СЂРµРєРѕРјРµРЅРґР°С†РёРё" in title:
        return "recommendations"
    if "pc/sc" in title:
        return "pcsc"
    return "general"


def enrich_chunk(document: SourceDocument, chunk: Chunk) -> Chunk:
    text_lower = chunk.text.lower()
    combined = f"{document.title} {' '.join(chunk.heading_path)} {chunk.text}"
    rule_entities = extract_named_entities(combined)

    language_tags = list(rule_entities.get("language_tags", []))
    if chunk.chunk_type == "code" and "python" not in language_tags:
        if "functionlist->" in text_lower or "ck_" in text_lower:
            language_tags.append("c")

    merged_entities = merge_named_entities(
        rule_entities,
        {"language_tags": unique_preserve(language_tags)},
    )

    metadata: dict[str, Any] = {
        "doc_family": classify_doc_family(document),
        "products": merged_entities.get("products", []),
        "interfaces": merged_entities.get("interfaces", []),
        "os_tags": merged_entities.get("os_tags", []),
        "language_tags": merged_entities.get("language_tags", []),
        "components": merged_entities.get("components", []),
        "api_symbols": merged_entities.get("api_symbols", []),
        "pkcs11_objects": merged_entities.get("pkcs11_objects", []),
        "pkcs11_mechanisms": merged_entities.get("pkcs11_mechanisms", []),
        "error_codes": merged_entities.get("error_codes", []),
        "entity_terms": entity_terms(merged_entities),
        "heading_path_text": " > ".join(chunk.heading_path),
        "chunk_type": chunk.chunk_type,
        "graph_entities_rule": merged_entities,
        "graph_entities_llm": {},
        "graph_relations": [],
        "graph_enrichment_version": GRAPH_METADATA_VERSION,
    }
    chunk.metadata.update(metadata)
    return chunk


def metadata_matches(metadata: dict[str, Any], filters: dict[str, list[str] | str]) -> bool:
    for key, value in filters.items():
        expected = [value] if isinstance(value, str) else value
        if not expected:
            continue
        actual = metadata.get(key)
        if isinstance(actual, list):
            if not set(expected).intersection(actual):
                return False
        elif actual not in expected:
            return False
    return True
