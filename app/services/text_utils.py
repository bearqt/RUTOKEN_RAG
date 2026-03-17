from __future__ import annotations

import re
from typing import Iterable


TOKEN_PATTERN = re.compile(r"[A-Za-zА-Яа-я0-9_./#+-]+")
SYMBOL_PATTERN = re.compile(r"\b(?:CKR|CKA|CKO|CKM|CKU|CKF)_[A-Z0-9_]+\b|\bC_[A-Za-z0-9_]+\b|\brt[A-Za-z0-9_]+\b")


def clean_inline_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = text.replace("\\#", "#").replace("\\_", "_")
    return re.sub(r"\s+", " ", text).strip()


def tokenize_for_bm25(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def extract_symbols(text: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for match in SYMBOL_PATTERN.findall(text):
        if match not in seen:
            seen.add(match)
            result.append(match)
    return result


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def unique_preserve(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

