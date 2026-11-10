from pathlib import Path

import pytest

from change_radar.cli import main
from change_radar.models import Alert, Item
from change_radar.store import Store

SOURCES = """
[[source]]
id = "test-feed"
name = "Test feed"
kind = "rss"
url = "https://example.com/feed.xml"
"""
NOTICE = "All payment aggregators must delete stored card data by September 30, 2022."


def prepare(tmp_path: Path, source_id: str) -> tuple[str, str]:
    notice = tmp_path / "notice.txt"
    notice.write_text(NOTICE + " Contact us for queries.\n")
    sources = tmp_path / "sources.toml"
    sources.write_text(SOURCES)
    db = str(tmp_path / "radar.sqlite")
    code = main(
        [
            "import",
            str(notice),
            "--url",
            "https://example.com/n",
            "--title",
            "Card data rule",
            "--source-id",
            source_id,
            "--db",
            db,
        ]
    )
    assert code == 0
    assert main(["extract", "--db", db]) == 0
    return db, str(sources)


def test_import_extract_digest_end_to_end(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db, sources = prepare(tmp_path, "manual")
    out = tmp_path / "digest.md"
    assert main(["digest", "--db", db, "--sources", sources, "--out", str(out)]) == 0
    text = out.read_text()
    assert "must delete stored card data" in text
    assert "<https://example.com/n>" in text
    assert "September 30, 2022" in text
    assert "hand-imported" in capsys.readouterr().err
    html_out = tmp_path / "digest.html"
    args = ["digest", "--db", db, "--sources", sources, "--format", "html", "--out"]
    assert main([*args, str(html_out)]) == 0
    assert html_out.read_text().startswith("<!doctype html>")


def test_digest_warns_about_sources_that_are_not_cleared(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db, sources = prepare(tmp_path, "test-feed")
    out = tmp_path / "digest.md"
    assert main(["digest", "--db", db, "--sources", sources, "--out", str(out)]) == 0
    assert "not cleared" in capsys.readouterr().err


def test_digest_skips_alerts_that_no_longer_verify(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = str(tmp_path / "radar.sqlite")
    item = Item(source_id="manual", url="https://example.com/n", title="T", text=NOTICE)
    bad = Alert(
        item_key=item.key,
        what_changed="x",
        who_it_affects="y",
        deadline="none stated",
        what_to_check="z",
        quote="This sentence is not in the notice at all",
        source_url=item.url,
    )
    with Store(db) as store:
        store.upsert_item(item)
        store.add_alert(bad)
    out = tmp_path / "digest.md"
    assert main(["digest", "--db", db, "--out", str(out)]) == 0
    assert "skipped an alert" in capsys.readouterr().err
    assert "No items." in out.read_text()


def test_import_rejects_a_bad_url(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    notice = tmp_path / "notice.txt"
    notice.write_text(NOTICE)
    code = main(["import", str(notice), "--url", "http://x.com", "--title", "T"])
    assert code == 2
    assert "https" in capsys.readouterr().err


def test_sources_command_lists_terms_status(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sources = tmp_path / "sources.toml"
    sources.write_text(SOURCES)
    assert main(["sources", "--sources", str(sources)]) == 0
    assert "TERMS NOT CLEARED" in capsys.readouterr().out


def test_fetch_skips_sources_that_are_not_cleared(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sources = tmp_path / "sources.toml"
    sources.write_text(SOURCES)
    db = str(tmp_path / "radar.sqlite")
    assert main(["fetch", "--sources", str(sources), "--db", db]) == 0
    out = capsys.readouterr().out
    assert "skipped 1 source" in out
    assert "nothing to fetch" in out
