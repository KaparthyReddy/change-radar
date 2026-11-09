"""Core data types shared across Change Radar."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

NO_DEADLINE = "none stated"


@dataclass(frozen=True, slots=True)
class Item:
    """A document published by an official source, as fetched."""

    source_id: str
    url: str
    title: str
    text: str
    published: datetime | None = None

    @property
    def key(self) -> str:
        """Stable identifier derived from the source and the URL."""
        raw = f"{self.source_id}\n{self.url}".encode()
        return hashlib.sha256(raw).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class Alert:
    """One alert about one item. The quote must appear verbatim in the item's text."""

    item_key: str
    what_changed: str
    who_it_affects: str
    deadline: str
    what_to_check: str
    quote: str
    source_url: str
