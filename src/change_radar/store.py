"""SQLite storage for fetched items and verified alerts."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Literal, Self

from change_radar.models import Alert, Item

ItemStatus = Literal["new", "changed", "unchanged"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    key TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    text_sha TEXT NOT NULL,
    published TEXT,
    first_seen TEXT NOT NULL,
    last_changed TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_key TEXT NOT NULL REFERENCES items(key),
    what_changed TEXT NOT NULL,
    who_it_affects TEXT NOT NULL,
    deadline TEXT NOT NULL,
    what_to_check TEXT NOT NULL,
    quote TEXT NOT NULL,
    source_url TEXT NOT NULL,
    created TEXT NOT NULL,
    UNIQUE (item_key, quote)
);
"""


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _to_item(row: sqlite3.Row) -> Item:
    published = datetime.fromisoformat(row["published"]) if row["published"] else None
    return Item(
        source_id=str(row["source_id"]),
        url=str(row["url"]),
        title=str(row["title"]),
        text=str(row["text"]),
        published=published,
    )


def _to_alert(row: sqlite3.Row) -> Alert:
    return Alert(
        item_key=str(row["item_key"]),
        what_changed=str(row["what_changed"]),
        who_it_affects=str(row["who_it_affects"]),
        deadline=str(row["deadline"]),
        what_to_check=str(row["what_to_check"]),
        quote=str(row["quote"]),
        source_url=str(row["source_url"]),
    )


class Store:
    """Stores items and alerts. Use ':memory:' for tests."""

    def __init__(self, path: Path | str = ":memory:") -> None:
        location = str(path)
        if location != ":memory:":
            Path(location).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(location)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(SCHEMA)

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def upsert_item(self, item: Item, *, now: datetime | None = None) -> ItemStatus:
        """Save an item. Reports whether it is new, changed since last seen, or unchanged.

        When an item changes, alerts made from its old text are kept and should be
        re-verified against the new text.
        """
        stamp = _iso(now or datetime.now(UTC))
        sha = _sha(item.text)
        published = _iso(item.published) if item.published else None
        row = self._db.execute("SELECT text_sha FROM items WHERE key = ?", (item.key,)).fetchone()
        if row is None:
            self._db.execute(
                "INSERT INTO items (key, source_id, url, title, text, text_sha, published,"
                " first_seen, last_changed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (item.key, item.source_id, item.url, item.title, item.text, sha, published,
                 stamp, stamp),
            )
            self._db.commit()
            return "new"
        if row["text_sha"] == sha:
            return "unchanged"
        self._db.execute(
            "UPDATE items SET title = ?, text = ?, text_sha = ?, published = ?,"
            " last_changed = ? WHERE key = ?",
            (item.title, item.text, sha, published, stamp, item.key),
        )
        self._db.commit()
        return "changed"

    def get_item(self, key: str) -> Item | None:
        row = self._db.execute("SELECT * FROM items WHERE key = ?", (key,)).fetchone()
        return _to_item(row) if row is not None else None

    def items(self, source_id: str | None = None) -> list[Item]:
        """All items, newest first, optionally limited to one source."""
        rows = self._db.execute(
            "SELECT * FROM items WHERE (? IS NULL OR source_id = ?)"
            " ORDER BY COALESCE(published, first_seen) DESC, key",
            (source_id, source_id),
        ).fetchall()
        return [_to_item(row) for row in rows]

    def add_alert(self, alert: Alert, *, now: datetime | None = None) -> bool:
        """Save a verified alert. Returns False if the same quote is already saved for the item."""
        stamp = _iso(now or datetime.now(UTC))
        cursor = self._db.execute(
            "INSERT OR IGNORE INTO alerts (item_key, what_changed, who_it_affects, deadline,"
            " what_to_check, quote, source_url, created) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (alert.item_key, alert.what_changed, alert.who_it_affects, alert.deadline,
             alert.what_to_check, alert.quote, alert.source_url, stamp),
        )
        self._db.commit()
        return cursor.rowcount == 1

    def alerts(self, item_key: str | None = None) -> list[Alert]:
        rows = self._db.execute(
            "SELECT * FROM alerts WHERE (? IS NULL OR item_key = ?) ORDER BY id",
            (item_key, item_key),
        ).fetchall()
        return [_to_alert(row) for row in rows]
