import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from change_radar.models import Alert, Item
from change_radar.store import Store

PUBLISHED = datetime(2026, 11, 9, 10, 0, tzinfo=UTC)


def make_item(text: str = "Some text.", url: str = "https://example.com/a") -> Item:
    return Item(source_id="rbi", url=url, title="Notice", text=text, published=PUBLISHED)


def make_alert(item: Item, quote: str = "The regulator has decided to extend it") -> Alert:
    return Alert(
        item_key=item.key,
        what_changed="Deadline extended",
        who_it_affects="Merchants",
        deadline="none stated",
        what_to_check="Whether your plan is affected",
        quote=quote,
        source_url=item.url,
    )


def test_upsert_reports_new_unchanged_and_changed() -> None:
    with Store() as store:
        item = make_item()
        assert store.upsert_item(item) == "new"
        assert store.upsert_item(item) == "unchanged"
        assert store.upsert_item(make_item(text="Different text.")) == "changed"


def test_get_item_round_trips() -> None:
    with Store() as store:
        item = make_item()
        store.upsert_item(item)
        assert store.get_item(item.key) == item
        assert store.get_item("missing") is None


def test_changed_text_is_saved() -> None:
    with Store() as store:
        store.upsert_item(make_item())
        updated = make_item(text="Different text.")
        store.upsert_item(updated)
        saved = store.get_item(updated.key)
        assert saved is not None
        assert saved.text == "Different text."


def test_items_can_be_filtered_by_source() -> None:
    with Store() as store:
        store.upsert_item(make_item(url="https://example.com/a"))
        store.upsert_item(
            Item(source_id="npci", url="https://example.com/b", title="Other", text="Text.")
        )
        assert len(store.items()) == 2
        assert [item.source_id for item in store.items("npci")] == ["npci"]


def test_add_alert_ignores_duplicates() -> None:
    with Store() as store:
        item = make_item()
        store.upsert_item(item)
        alert = make_alert(item)
        assert store.add_alert(alert)
        assert not store.add_alert(alert)
        assert store.alerts() == [alert]
        assert store.alerts(item.key) == [alert]
        assert store.alerts("other") == []


def test_alert_for_unknown_item_is_rejected() -> None:
    with Store() as store, pytest.raises(sqlite3.IntegrityError):
        store.add_alert(make_alert(make_item()))


def test_data_persists_between_sessions(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "radar.sqlite"
    item = make_item()
    with Store(path) as store:
        store.upsert_item(item)
    with Store(path) as store:
        assert store.get_item(item.key) == item
