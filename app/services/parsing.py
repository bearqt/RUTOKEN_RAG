from __future__ import annotations

import re
from pathlib import Path

from app.domain.models import Chunk, SourceDocument
from app.services.enrichment import enrich_chunk
from app.services.text_utils import clean_inline_markdown, normalize_whitespace


TITLE_LINK_PATTERN = re.compile(r"^\[(?P<title>.+?)\]\((?P<url>https://dev\.rutoken\.ru/pages/viewpage\.action\?pageId=(?P<page_id>\d+))\)")
CREATED_BY_PATTERN = re.compile(
    r"Created by \[(?P<author>.+?)\]\([^)]+\), (?:(?:last modified by \[[^\]]+\]\([^)]+\) on)|last modified on) \[(?P<modified>[^\]]+)\]"
)
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")


def load_source_documents(scrape_dir: Path) -> list[SourceDocument]:
    documents: list[SourceDocument] = []
    for path in sorted(scrape_dir.glob("*.md")):
        documents.append(parse_source_document(path))
    return documents


def parse_source_document(path: Path) -> SourceDocument:
    raw_markdown = path.read_text(encoding="utf-8")
    lines = raw_markdown.splitlines()

    title_match = TITLE_LINK_PATTERN.match(lines[0].strip())
    if not title_match:
        raise ValueError(f"Cannot parse title line in {path}")

    author = None
    modified = None
    for line in lines[:20]:
        created_match = CREATED_BY_PATTERN.search(line)
        if created_match:
            author = clean_inline_markdown(created_match.group("author"))
            modified = created_match.group("modified")
            break

    clean_markdown = cleanup_markdown(lines)
    return SourceDocument(
        document_id=path.stem,
        page_id=title_match.group("page_id"),
        source_url=title_match.group("url"),
        title=clean_inline_markdown(title_match.group("title")),
        author=author,
        last_modified=modified,
        raw_markdown=raw_markdown,
        clean_markdown=clean_markdown,
    )


def cleanup_markdown(lines: list[str]) -> str:
    cleaned: list[str] = []
    in_comment_section = False
    in_code_block = False

    for index, raw_line in enumerate(lines):
        line = raw_line.rstrip()
        stripped = line.strip()

        if index == 0:
            continue

        if stripped.startswith("## ") and "Comment" in stripped:
            in_comment_section = True
        if in_comment_section:
            continue

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            cleaned.append(line)
            continue

        if in_code_block:
            cleaned.append(line)
            continue

        if not stripped:
            cleaned.append("")
            continue
        if stripped in {"-", "Loading...", "No labels", "Развернуть/Свернуть все"}:
            continue
        if stripped == "[▲▼](https://dev.rutoken.ru/pages/viewpage.action?pageId=2228237#)":
            continue
        if stripped.startswith("Created by "):
            continue
        if stripped.startswith("###### ![]("):
            continue
        if re.match(r"^#{1,6}\s*!\[[^\]]*\]\([^)]+\)\s*$", stripped):
            continue

        cleaned.append(line)

    return normalize_whitespace("\n".join(cleaned))


def build_chunks(
    document: SourceDocument,
    chunk_target_chars: int,
    chunk_overlap_chars: int,
    table_row_window: int,
) -> list[Chunk]:
    blocks = _extract_blocks(document.clean_markdown)
    chunks: list[Chunk] = []
    chunk_counter = 0
    previous_short_prose = ""

    for block_type, heading_path, text in blocks:
        if block_type == "prose":
            if len(text) <= 120:
                previous_short_prose = text
            for piece in _split_prose(text, chunk_target_chars, chunk_overlap_chars):
                if not piece.strip():
                    continue
                chunk_counter += 1
                chunks.append(
                    enrich_chunk(
                        document,
                        Chunk(
                            chunk_id=f"{document.document_id}-{chunk_counter:05d}",
                            document_id=document.document_id,
                            page_id=document.page_id,
                            source_url=document.source_url,
                            title=document.title,
                            heading_path=heading_path,
                            text=piece,
                            chunk_type="prose",
                        ),
                    )
                )
            continue

        if block_type == "table":
            prefix = previous_short_prose if previous_short_prose and len(previous_short_prose) <= 100 else ""
            previous_short_prose = ""
            for piece in _split_table(text, table_row_window):
                joined = f"{prefix}\n\n{piece}".strip() if prefix else piece
                chunk_counter += 1
                chunks.append(
                    enrich_chunk(
                        document,
                        Chunk(
                            chunk_id=f"{document.document_id}-{chunk_counter:05d}",
                            document_id=document.document_id,
                            page_id=document.page_id,
                            source_url=document.source_url,
                            title=document.title,
                            heading_path=heading_path,
                            text=joined,
                            chunk_type="table",
                        ),
                    )
                )
            continue

        previous_short_prose = ""
        for piece in _split_code(text, chunk_target_chars):
            chunk_counter += 1
            chunks.append(
                enrich_chunk(
                    document,
                    Chunk(
                        chunk_id=f"{document.document_id}-{chunk_counter:05d}",
                        document_id=document.document_id,
                        page_id=document.page_id,
                        source_url=document.source_url,
                        title=document.title,
                        heading_path=heading_path,
                        text=piece,
                        chunk_type="code",
                    ),
                )
            )

    return chunks


def _extract_blocks(markdown: str) -> list[tuple[str, list[str], str]]:
    lines = markdown.splitlines()
    heading_stack: list[str] = []
    blocks: list[tuple[str, list[str], str]] = []
    buffer: list[str] = []

    def flush_buffer() -> None:
        nonlocal buffer
        text = normalize_whitespace("\n".join(buffer))
        if text:
            blocks.append(("prose", heading_stack.copy(), text))
        buffer = []

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        heading_match = HEADING_PATTERN.match(stripped)
        if heading_match:
            flush_buffer()
            depth = len(heading_match.group(1))
            title = clean_inline_markdown(heading_match.group(2))
            heading_stack = heading_stack[: depth - 1]
            heading_stack.append(title)
            index += 1
            continue

        if stripped.startswith("```"):
            flush_buffer()
            code_lines = [line]
            index += 1
            while index < len(lines):
                code_lines.append(lines[index])
                if lines[index].strip().startswith("```"):
                    index += 1
                    break
                index += 1
            blocks.append(("code", heading_stack.copy(), "\n".join(code_lines).strip()))
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            flush_buffer()
            table_lines = [line]
            index += 1
            while index < len(lines):
                table_line = lines[index].strip()
                if table_line.startswith("|") and table_line.endswith("|"):
                    table_lines.append(lines[index])
                    index += 1
                    continue
                break
            blocks.append(("table", heading_stack.copy(), "\n".join(table_lines).strip()))
            continue

        buffer.append(line)
        index += 1

    flush_buffer()
    return blocks


def _split_prose(text: str, target: int, overlap: int) -> list[str]:
    if len(text) <= target:
        return [text]

    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= target:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= target:
            current = paragraph
            continue

        start = 0
        while start < len(paragraph):
            end = min(len(paragraph), start + target)
            chunks.append(paragraph[start:end].strip())
            if end == len(paragraph):
                break
            start = max(end - overlap, 0)
        current = ""

    if current:
        chunks.append(current)
    return chunks


def _split_table(text: str, row_window: int) -> list[str]:
    lines = text.splitlines()
    if len(lines) <= row_window + 2:
        return [text]
    header = lines[:2]
    rows = lines[2:]
    chunks: list[str] = []
    for index in range(0, len(rows), row_window):
        chunks.append("\n".join(header + rows[index : index + row_window]))
    return chunks


def _split_code(text: str, target: int) -> list[str]:
    if len(text) <= target:
        return [text]
    lines = text.splitlines()
    chunks: list[str] = []
    window = 80
    overlap = 10
    start = 0
    while start < len(lines):
        end = min(len(lines), start + window)
        block = "\n".join(lines[start:end]).strip()
        if not block.startswith("```"):
            block = f"```\n{block}"
        if not block.endswith("```"):
            block = f"{block}\n```"
        chunks.append(block)
        if end == len(lines):
            break
        start = max(end - overlap, 0)
    return chunks

