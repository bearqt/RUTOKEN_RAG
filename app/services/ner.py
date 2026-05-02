from __future__ import annotations

import re

from app.services.text_utils import extract_symbols, unique_preserve


PRODUCTS = {
    "СЂСѓС‚РѕРєРµРЅ s": "rutoken_s",
    "rutoken s": "rutoken_s",
    "СЂСѓС‚РѕРєРµРЅ lite": "rutoken_lite",
    "rutoken lite": "rutoken_lite",
    "СЂСѓС‚РѕРєРµРЅ СЌС†Рї 2.0 (2000)": "rutoken_ecp_2000",
    "СЂСѓС‚РѕРєРµРЅ СЌС†Рї 2.0 2000": "rutoken_ecp_2000",
    "СЂСѓС‚РѕРєРµРЅ СЌС†Рї 2.0 2100": "rutoken_ecp_2100",
    "СЂСѓС‚РѕРєРµРЅ СЌС†Рї pki": "rutoken_ecp_pki",
    "СЂСѓС‚РѕРєРµРЅ СЌС†Рї 2.0 flash": "rutoken_ecp_flash",
    "СЂСѓС‚РѕРєРµРЅ СЌС†Рї 2.0 3000": "rutoken_ecp_3000",
    "СЂСѓС‚РѕРєРµРЅ СЌС†Рї 3.0 3100": "rutoken_ecp_3100",
    "СЂСѓС‚РѕРєРµРЅ СЌС†Рї 3.0 nfc 3100": "rutoken_ecp_nfc_3100",
    "СЂСѓС‚РѕРєРµРЅ СЌС†Рї 3.0 3220": "rutoken_ecp_3220",
    "СЂСѓС‚РѕРєРµРЅ СЌС†Рї 3.0 3120": "rutoken_ecp_3120",
    "СЂСѓС‚РѕРєРµРЅ keybox": "rutoken_keybox",
    "rutoken keybox": "rutoken_keybox",
    "keybox": "rutoken_keybox",
}

INTERFACES = {
    "pkcs#11": "pkcs11",
    "pkcs 11": "pkcs11",
    "cryptoki": "pkcs11",
    "cryptoapi": "cryptoapi",
    "csp": "csp",
    "cng": "cng",
    "pc/sc": "pcsc",
    "pcsc": "pcsc",
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
    "aurora": "aurora",
    "Р°РІСЂРѕСЂР°": "aurora",
    "unix": "unix",
}

LANGUAGE_HINTS = {
    "python": "python",
    "c++": "cpp",
    "c#": "csharp",
    "java": "java",
    "javascript": "javascript",
    "go": "go",
    "c": "c",
}

COMPONENTS = {
    "keybox": "keybox",
    "СЂСѓС‚РѕРєРµРЅ keybox": "keybox",
    "С†РµРЅС‚СЂ СѓРїСЂР°РІР»РµРЅРёСЏ СЂСѓС‚РѕРєРµРЅ": "cur",
    "С†СѓСЂ": "cur",
    "rtengine": "rtengine",
    "opensc": "opensc",
    "osslsigncode": "osslsigncode",
    "РєСЂРёРїС‚РѕРїСЂРѕ": "cryptopro",
    "cryptopro": "cryptopro",
    "rtpcsc": "rtpcsc",
    "pc/sc service": "rtpcsc",
    "ldap": "ldap",
    "msca": "msca",
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "nginx": "nginx",
    "apache": "apache",
    "iis": "iis",
}

PKCS11_OBJECT_PATTERN = re.compile(r"\b(?:CKA|CKO|CKU|CKF)_[A-Z0-9_]+\b")
PKCS11_MECHANISM_PATTERN = re.compile(r"\bCKM_[A-Z0-9_]+\b")
ERROR_CODE_PATTERN = re.compile(r"\bCKR_[A-Z0-9_]+\b")
CODE_REFERENCE_PATTERN = re.compile(r"\bC_[A-Za-z0-9_]+\b|\brt[A-Za-z0-9_]+\b")

ENTITY_ALIASES = {
    "products": PRODUCTS,
    "interfaces": INTERFACES,
    "os_tags": OPERATING_SYSTEMS,
    "language_tags": LANGUAGE_HINTS,
    "components": COMPONENTS,
}

ENTITY_FIELDS = (
    "products",
    "interfaces",
    "os_tags",
    "language_tags",
    "components",
    "api_symbols",
    "pkcs11_objects",
    "pkcs11_mechanisms",
    "error_codes",
)

CANONICAL_ENTITY_VALUES = {
    entity_type: set(aliases.values())
    for entity_type, aliases in ENTITY_ALIASES.items()
}


def extract_named_entities(text: str) -> dict[str, list[str]]:
    normalized = text.lower()
    raw_symbols = extract_symbols(text)
    entities = {
        "products": _extract_aliases(normalized, PRODUCTS),
        "interfaces": _extract_aliases(normalized, INTERFACES),
        "os_tags": _extract_aliases(normalized, OPERATING_SYSTEMS),
        "language_tags": _extract_aliases(normalized, LANGUAGE_HINTS),
        "components": _extract_aliases(normalized, COMPONENTS),
        "api_symbols": [
            value
            for value in raw_symbols
            if canonicalize_entity_value("api_symbols", value) is not None
        ],
        "pkcs11_objects": _extract_pattern(text, PKCS11_OBJECT_PATTERN),
        "pkcs11_mechanisms": _extract_pattern(text, PKCS11_MECHANISM_PATTERN),
        "error_codes": _extract_pattern(text, ERROR_CODE_PATTERN),
    }
    return {key: unique_preserve(values) for key, values in entities.items() if values}


def merge_named_entities(*entities_list: dict[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for entities in entities_list:
        for key, values in entities.items():
            if not values:
                continue
            normalized_values = [
                canonical
                for value in values
                if (canonical := canonicalize_entity_value(key, value)) is not None
            ]
            if not normalized_values:
                continue
            merged[key] = unique_preserve([*merged.get(key, []), *normalized_values])
    return merged


def entity_terms(entities: dict[str, list[str]]) -> list[str]:
    terms: list[str] = []
    for key in ENTITY_FIELDS:
        terms.extend(entities.get(key, []))
    return unique_preserve(terms)


def augment_query_with_entities(query: str, entities: dict[str, list[str]]) -> str:
    additions = entity_terms(entities)
    if not additions:
        return query
    return f"{query} {' '.join(additions)}"


def canonicalize_entity_value(entity_type: str, value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None

    if entity_type in ENTITY_ALIASES:
        lowered = candidate.lower()
        alias_match = ENTITY_ALIASES[entity_type].get(lowered)
        if alias_match:
            return alias_match
        if lowered in CANONICAL_ENTITY_VALUES[entity_type]:
            return lowered
        return None

    if entity_type == "api_symbols":
        return candidate if CODE_REFERENCE_PATTERN.fullmatch(candidate) else None

    if entity_type == "pkcs11_objects":
        upper = candidate.upper()
        return upper if PKCS11_OBJECT_PATTERN.fullmatch(upper) else None

    if entity_type == "pkcs11_mechanisms":
        upper = candidate.upper()
        return upper if PKCS11_MECHANISM_PATTERN.fullmatch(upper) else None

    if entity_type == "error_codes":
        upper = candidate.upper()
        return upper if ERROR_CODE_PATTERN.fullmatch(upper) else None

    return None


def entity_aliases(entity_type: str, canonical_value: str) -> list[str]:
    aliases = ENTITY_ALIASES.get(entity_type)
    if aliases is None:
        return [canonical_value]
    return unique_preserve(
        [label for label, value in aliases.items() if value == canonical_value] + [canonical_value]
    )


def _extract_aliases(text: str, aliases: dict[str, str]) -> list[str]:
    return unique_preserve(tag for label, tag in aliases.items() if label in text)


def _extract_pattern(text: str, pattern: re.Pattern[str]) -> list[str]:
    return unique_preserve(match.upper() for match in pattern.findall(text))
