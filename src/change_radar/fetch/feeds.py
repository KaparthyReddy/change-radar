"""Parse RSS and Atom feeds into Items."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

from change_radar.config import Source
from change_radar.fetch.http import Fetcher
from change_radar.fetch.text import html_to_text
from change_radar.models import Item

ATOM = "{http://www.w3.org/2005/Atom}"


class FeedError(ValueError):
    """Raised when a feed cannot be parsed."""


def _text(element: Any, tag: str) -> str:
    child = element.find(tag)
    if child is None or child.text is None:
        return ""
    return str(child.text).strip()


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _build(source: Source, title: str, link: str, body: str, published: str) -> Item | None:
    if not title or not link.startswith(("https://", "http://")):
        return None
    text = html_to_text(body) if body else ""
    return Item(
        source_id=source.id,
        url=link,
        title=title,
        text=text or title,
        published=_parse_date(published),
    )


def _rss_item(node: Any, source: Source) -> Item | None:
    return _build(
        source,
        _text(node, "title"),
        _text(node, "link"),
        _text(node, "description"),
        _text(node, "pubDate"),
    )


def _atom_item(node: Any, source: Source) -> Item | None:
    link = ""
    for candidate in node.findall(f"{ATOM}link"):
        if candidate.get("rel", "alternate") == "alternate":
            link = str(candidate.get("href", "")).strip()
            break
    body = _text(node, f"{ATOM}content") or _text(node, f"{ATOM}summary")
    published = _text(node, f"{ATOM}published") or _text(node, f"{ATOM}updated")
    return _build(source, _text(node, f"{ATOM}title"), link, body, published)


def parse_feed(data: bytes, source: Source) -> list[Item]:
    """Parse RSS 2.0 or Atom bytes into Items. Entries without a title or link are skipped."""
    if b"<!ENTITY" in data:
        raise FeedError("feed declares XML entities; refusing to parse it")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise FeedError(f"feed is not valid XML: {exc}") from exc
    candidates = [_rss_item(node, source) for node in root.iter("item")]
    candidates += [_atom_item(node, source) for node in root.iter(f"{ATOM}entry")]
    unique: dict[str, Item] = {}
    for item in candidates:
        if item is not None:
            unique.setdefault(item.key, item)
    return list(unique.values())


def fetch_feed(source: Source, fetcher: Fetcher) -> list[Item]:
    """Fetch a source's feed with the given fetcher and parse it."""
    return parse_feed(fetcher(source.url), source)
