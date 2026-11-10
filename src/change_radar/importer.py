"""Import a document you read by hand, so it can be processed with no network access."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from change_radar.fetch.text import html_to_text
from change_radar.models import Item

HTML_SUFFIXES = frozenset({".html", ".htm"})


class DocumentError(ValueError):
    """Raised when a document cannot be imported."""


def parse_published(value: str) -> datetime:
    """Parse a date such as 2026-11-09. Dates without a time zone are treated as UTC."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise DocumentError(f"published must look like 2026-11-09, got: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _plain_text(raw: str) -> str:
    lines = (" ".join(line.split()) for line in raw.splitlines())
    return "\n".join(line for line in lines if line)


def load_document(
    path: Path,
    *,
    url: str,
    title: str,
    source_id: str = "manual",
    published: str | None = None,
) -> Item:
    """Read a text or HTML file into an Item. The URL must be the page it came from."""
    if not url.startswith("https://"):
        raise DocumentError("url must start with https://")
    clean_title = " ".join(title.split())
    if not clean_title:
        raise DocumentError("title is required")
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise DocumentError(f"file not found: {path}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise DocumentError(f"could not read {path}: {exc}") from exc
    is_html = path.suffix.lower() in HTML_SUFFIXES
    text = html_to_text(raw) if is_html else _plain_text(raw)
    if not text:
        raise DocumentError(f"{path} contains no text")
    return Item(
        source_id=source_id.strip() or "manual",
        url=url,
        title=clean_title,
        text=text,
        published=parse_published(published) if published else None,
    )
