from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from firecrawl import Firecrawl


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_START_URL = "https://dev.rutoken.ru/"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "scrape_result"

PAGE_ID_PATTERN = re.compile(r"[?&]pageId=(\d+)\b")
MARKDOWN_TITLE_LINK_PATTERN = re.compile(
    r"^\[(?P<title>.+?)\]\((?P<url>https://dev\.rutoken\.ru/[^)]+)\)"
)


@dataclass(frozen=True)
class SavedDocument:
    path: str
    source_url: str
    title: str
    page_id: str | None
    status_code: int | None


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    args = parse_args()

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise SystemExit("FIRECRAWL_API_KEY is not set")

    output_dir = resolve_output_dir(args.output_dir)
    if args.clean:
        clean_markdown_files(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    firecrawl = Firecrawl(api_key=api_key)
    crawl = firecrawl.crawl(
        url=args.start_url,
        limit=args.limit,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
        max_discovery_depth=args.max_discovery_depth,
        crawl_entire_domain=True,
        allow_subdomains=False,
        allow_external_links=False,
        ignore_query_parameters=False,
        regex_on_full_url=True,
        include_paths=[
            r"^https://dev\.rutoken\.ru/$",
            r"^https://dev\.rutoken\.ru/pages/viewpage\.action\?pageId=\d+.*",
            r"^https://dev\.rutoken\.ru/display/.*",
        ],
        exclude_paths=[
            r"^https://dev\.rutoken\.ru/login\.action.*",
            r"^https://dev\.rutoken\.ru/pages/diffpages.*",
            r"^https://dev\.rutoken\.ru/pages/editpage.*",
            r"^https://dev\.rutoken\.ru/pages/createpage.*",
            r"^https://dev\.rutoken\.ru/pages/viewpreviousversions.*",
            r"^https://dev\.rutoken\.ru/download/.*",
            r"^https://dev\.rutoken\.ru/rest/.*",
            r"^https://dev\.rutoken\.ru/plugins/.*",
            r"^https://dev\.rutoken\.ru/users/.*",
        ],
        scrape_options={
            "formats": ["markdown"],
            "only_main_content": True,
            "max_age": args.max_age,
        },
    )

    documents = iter_documents(crawl)
    saved: list[SavedDocument] = []
    skipped = 0

    for document in documents:
        record = save_document(
            document=document,
            output_dir=output_dir,
            skip_without_page_id=args.skip_without_page_id,
        )
        if record is None:
            skipped += 1
            continue
        saved.append(record)

    manifest = {
        "start_url": args.start_url,
        "output_dir": str(output_dir.relative_to(PROJECT_ROOT)),
        "total_returned": len(documents),
        "saved": len(saved),
        "skipped": skipped,
        "documents": [asdict(record) for record in saved],
    }
    (output_dir / "_crawl_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved markdown documents: {len(saved)}")
    print(f"Skipped documents: {skipped}")
    print(f"Output directory: {output_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl dev.rutoken.ru with Firecrawl and save Markdown files into scrape_result.",
    )
    parser.add_argument("--start-url", default=DEFAULT_START_URL)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--max-discovery-depth", type=int, default=8)
    parser.add_argument("--poll-interval", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument(
        "--max-age",
        type=int,
        default=0,
        help="Firecrawl cache age in ms; 0 requests fresh data.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing *.md files in output dir before crawling.",
    )
    parser.add_argument(
        "--keep-without-page-id",
        dest="skip_without_page_id",
        action="store_false",
        help="Also save pages where pageId cannot be extracted. These files may not be ingest-compatible.",
    )
    parser.set_defaults(skip_without_page_id=True)
    return parser.parse_args()


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def resolve_output_dir(raw_path: str) -> Path:
    output_dir = Path(raw_path)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir = output_dir.resolve()
    try:
        output_dir.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise SystemExit(f"Output directory must be inside project root: {output_dir}") from exc
    return output_dir


def clean_markdown_files(output_dir: Path) -> None:
    if not output_dir.exists():
        return

    output_dir = output_dir.resolve()
    try:
        output_dir.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise SystemExit(f"Refusing to clean directory outside project root: {output_dir}") from exc

    for path in output_dir.glob("*.md"):
        path.unlink()


def iter_documents(crawl: Any) -> list[Any]:
    data = get_value(crawl, "data")
    if data is None and isinstance(crawl, list):
        return crawl
    if data is None and isinstance(crawl, dict):
        data = crawl.get("data")
    if data is None:
        raise RuntimeError("Firecrawl response does not contain a data collection")
    return list(data)


def save_document(
    document: Any,
    output_dir: Path,
    skip_without_page_id: bool,
) -> SavedDocument | None:
    metadata = get_value(document, "metadata", default={}) or {}
    markdown = (get_value(document, "markdown", default="") or "").strip()
    if not markdown:
        return None

    status_code = get_status_code(metadata)
    if status_code is not None and status_code >= 400:
        return None

    source_url = get_source_url(document, metadata, markdown)
    if not source_url or not source_url.startswith("https://dev.rutoken.ru/"):
        return None

    found_page_id = extract_page_id(source_url) or extract_page_id(markdown)
    if found_page_id is None and skip_without_page_id:
        return None

    document_title = get_title(metadata, markdown, source_url)
    header_url = source_url
    if found_page_id is not None and "pageId=" not in header_url:
        header_url = f"https://dev.rutoken.ru/pages/viewpage.action?pageId={found_page_id}"

    body = strip_existing_title_line(markdown)
    content = f"[{escape_link_text(document_title)}]({header_url})\n\n{body}\n"

    filename = (
        f"pageId_{found_page_id}.md"
        if found_page_id
        else f"{slugify(document_title)}-{short_hash(source_url)}.md"
    )
    path = output_dir / filename
    path.write_text(content, encoding="utf-8")

    return SavedDocument(
        path=str(path.relative_to(PROJECT_ROOT)),
        source_url=source_url,
        title=document_title,
        page_id=found_page_id,
        status_code=status_code,
    )


def get_value(container: Any, key: str, default: Any = None) -> Any:
    if isinstance(container, dict):
        return container.get(key, default)
    return getattr(container, key, default)


def get_metadata_value(metadata: Any, *keys: str) -> Any:
    for key in keys:
        value = get_value(metadata, key)
        if value not in (None, ""):
            return value
    return None


def get_status_code(metadata: Any) -> int | None:
    raw_status = get_metadata_value(metadata, "status_code", "statusCode")
    if raw_status is None:
        return None
    try:
        return int(raw_status)
    except (TypeError, ValueError):
        return None


def get_source_url(document: Any, metadata: Any, markdown: str) -> str | None:
    raw_url = (
        get_metadata_value(metadata, "source_url", "sourceURL", "url")
        or get_value(document, "url")
        or get_first_markdown_url(markdown)
    )
    if raw_url is None:
        return None
    return str(raw_url).split("#", 1)[0]


def get_title(metadata: Any, markdown: str, source_url: str) -> str:
    metadata_title = get_metadata_value(metadata, "title", "og_title", "ogTitle")
    if metadata_title:
        return str(metadata_title).strip()

    lines = markdown.splitlines()
    first_link = MARKDOWN_TITLE_LINK_PATTERN.match(lines[0].strip()) if lines else None
    if first_link:
        return first_link.group("title").strip()

    parsed = urlparse(source_url)
    fallback = Path(parsed.path).name or parsed.netloc
    return fallback.replace("-", " ").replace("_", " ").strip() or source_url


def get_first_markdown_url(markdown: str) -> str | None:
    if not markdown:
        return None
    first_line = markdown.splitlines()[0].strip()
    match = MARKDOWN_TITLE_LINK_PATTERN.match(first_line)
    return match.group("url") if match else None


def extract_page_id(value: str) -> str | None:
    match = PAGE_ID_PATTERN.search(value)
    if match:
        return match.group(1)

    parsed = urlparse(value)
    query_page_id = parse_qs(parsed.query).get("pageId")
    if query_page_id:
        return query_page_id[0]
    return None


def strip_existing_title_line(markdown: str) -> str:
    lines = markdown.splitlines()
    if not lines:
        return ""

    first_line = lines[0].strip()
    if MARKDOWN_TITLE_LINK_PATTERN.match(first_line) or first_line == "-":
        return "\n".join(lines[1:]).strip()
    return markdown.strip()


def escape_link_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return slug[:80] or "document"


def short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


if __name__ == "__main__":
    sys.exit(main())
