from __future__ import annotations

from typing import Any

from app.domain.models import Chunk, SourceDocument
from app.services.ner import entity_terms, extract_named_entities
from app.services.text_utils import extract_symbols, unique_preserve


def classify_doc_family(document: SourceDocument) -> str:
    title = document.title.lower()
    if "архитектура" in title:
        return "architecture"
    if "обзорная информация" in title or "сравнение технических характеристик" in title:
        return "product_matrix"
    if "объект" in title and "pkcs" in title:
        return "pkcs11_objects"
    if "хранилищ" in title:
        return "storage"
    if "выбор" in title or "рекомендации" in title:
        return "recommendations"
    if "pc/sc" in title:
        return "pcsc"
    return "general"


def enrich_chunk(document: SourceDocument, chunk: Chunk) -> Chunk:
    text_lower = chunk.text.lower()
    heading_lower = " ".join(chunk.heading_path).lower()
    combined = f"{document.title} {' '.join(chunk.heading_path)} {chunk.text}"
    entities = extract_named_entities(combined)

    products = entities.get("products", [])
    interfaces = entities.get("interfaces", [])
    os_tags = entities.get("os_tags", [])
    language_tags = entities.get("language_tags", [])
    components = entities.get("components", [])
    api_symbols = entities.get("api_symbols", [])

    if chunk.chunk_type == "code" and "python" not in language_tags:
        if "functionlist->" in text_lower or "ck_" in text_lower:
            language_tags.append("c")

    metadata: dict[str, Any] = {
        "doc_family": classify_doc_family(document),
        "products": unique_preserve(products),
        "interfaces": unique_preserve(interfaces),
        "os_tags": unique_preserve(os_tags),
        "language_tags": unique_preserve(language_tags),
        "components": unique_preserve(components),
        "api_symbols": unique_preserve([*api_symbols, *extract_symbols(" ".join(chunk.heading_path))]),
        "entity_terms": entity_terms(entities),
        "heading_path_text": " > ".join(chunk.heading_path),
        "chunk_type": chunk.chunk_type,
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
