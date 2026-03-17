from __future__ import annotations

from typing import Any

from app.domain.models import Chunk, SourceDocument
from app.services.text_utils import extract_symbols, unique_preserve


PRODUCTS = {
    "рутокен s": "rutoken_s",
    "рутокен lite": "rutoken_lite",
    "рутокен эцп 2.0 (2000)": "rutoken_ecp_2000",
    "рутокен эцп 2.0 2100": "rutoken_ecp_2100",
    "рутокен эцп pki": "rutoken_ecp_pki",
    "рутокен эцп 2.0 flash": "rutoken_ecp_flash",
    "рутокен эцп 2.0 3000": "rutoken_ecp_3000",
    "рутокен эцп 3.0 3100": "rutoken_ecp_3100",
    "рутокен эцп 3.0 nfc 3100": "rutoken_ecp_nfc_3100",
    "рутокен эцп 3.0 3220": "rutoken_ecp_3220",
    "рутокен эцп 3.0 3120": "rutoken_ecp_3120",
}

INTERFACES = {
    "pkcs#11": "pkcs11",
    "pkcs 11": "pkcs11",
    "cryptoki": "pkcs11",
    "cryptoapi": "cryptoapi",
    "cng": "cng",
    "pc/sc": "pcsc",
    "ccid": "ccid",
    "iso/iec 7816": "iso7816",
    "minidriver": "minidriver",
}

OPERATING_SYSTEMS = {
    "windows": "windows",
    "linux": "linux",
    "gnu/linux": "linux",
    "mac os": "macos",
    "macos": "macos",
    "android": "android",
    "ios": "ios",
    "ipados": "ios",
    "аврора": "aurora",
    "unix": "unix",
}

LANGUAGE_HINTS = {
    "python": "python",
    "c++": "cpp",
    "c#": "csharp",
    "java": "java",
    "javascript": "javascript",
    "go": "go",
}


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
    combined = f"{document.title.lower()} {heading_lower} {text_lower}"

    products = [tag for label, tag in PRODUCTS.items() if label in combined]
    interfaces = [tag for label, tag in INTERFACES.items() if label in combined]
    os_tags = [tag for label, tag in OPERATING_SYSTEMS.items() if label in combined]
    language_tags = [tag for label, tag in LANGUAGE_HINTS.items() if label in combined]

    if chunk.chunk_type == "code" and "python" not in language_tags:
        if "functionlist->" in text_lower or "ck_" in text_lower:
            language_tags.append("c")

    metadata: dict[str, Any] = {
        "doc_family": classify_doc_family(document),
        "products": unique_preserve(products),
        "interfaces": unique_preserve(interfaces),
        "os_tags": unique_preserve(os_tags),
        "language_tags": unique_preserve(language_tags),
        "api_symbols": extract_symbols(chunk.text),
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

