from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import Chunk


def save_chunks(path: Path, chunks: list[Chunk]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk.to_record(), ensure_ascii=False) + "\n")


def load_chunks(path: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    if not path.exists():
        return chunks
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            record = json.loads(line)
            chunks.append(Chunk(**record))
    return chunks

