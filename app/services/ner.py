from __future__ import annotations

from app.services.text_utils import extract_symbols, unique_preserve


PRODUCTS = {
    "рутокен s": "rutoken_s",
    "rutoken s": "rutoken_s",
    "рутокен lite": "rutoken_lite",
    "rutoken lite": "rutoken_lite",
    "рутокен эцп 2.0 (2000)": "rutoken_ecp_2000",
    "рутокен эцп 2.0 2000": "rutoken_ecp_2000",
    "рутокен эцп 2.0 2100": "rutoken_ecp_2100",
    "рутокен эцп pki": "rutoken_ecp_pki",
    "рутокен эцп 2.0 flash": "rutoken_ecp_flash",
    "рутокен эцп 2.0 3000": "rutoken_ecp_3000",
    "рутокен эцп 3.0 3100": "rutoken_ecp_3100",
    "рутокен эцп 3.0 nfc 3100": "rutoken_ecp_nfc_3100",
    "рутокен эцп 3.0 3220": "rutoken_ecp_3220",
    "рутокен эцп 3.0 3120": "rutoken_ecp_3120",
    "рутокен keybox": "rutoken_keybox",
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

COMPONENTS = {
    "keybox": "keybox",
    "рутокен keybox": "keybox",
    "центр управления рутокен": "cur",
    "цур": "cur",
    "rtengine": "rtengine",
    "opensc": "opensc",
    "osslsigncode": "osslsigncode",
    "криптопро": "cryptopro",
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

ENTITY_FIELDS = (
    "products",
    "interfaces",
    "os_tags",
    "language_tags",
    "components",
    "api_symbols",
)


def extract_named_entities(text: str) -> dict[str, list[str]]:
    normalized = text.lower()
    entities = {
        "products": _extract_aliases(normalized, PRODUCTS),
        "interfaces": _extract_aliases(normalized, INTERFACES),
        "os_tags": _extract_aliases(normalized, OPERATING_SYSTEMS),
        "language_tags": _extract_aliases(normalized, LANGUAGE_HINTS),
        "components": _extract_aliases(normalized, COMPONENTS),
        "api_symbols": extract_symbols(text),
    }
    return {key: value for key, value in entities.items() if value}


def merge_named_entities(*entities_list: dict[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for entities in entities_list:
        for key, values in entities.items():
            if not values:
                continue
            merged[key] = unique_preserve([*merged.get(key, []), *values])
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


def _extract_aliases(text: str, aliases: dict[str, str]) -> list[str]:
    return unique_preserve(tag for label, tag in aliases.items() if label in text)
