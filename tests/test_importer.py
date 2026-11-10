from pathlib import Path

import pytest

from change_radar.importer import DocumentError, load_document, parse_published


def test_imports_plain_text(tmp_path: Path) -> None:
    path = tmp_path / "notice.txt"
    path.write_text("First line.\n\n  Second   line.\n")
    item = load_document(path, url="https://example.com/n", title="  A   notice ")
    assert item.text == "First line.\nSecond line."
    assert item.title == "A notice"
    assert item.source_id == "manual"
    assert item.published is None


def test_imports_html(tmp_path: Path) -> None:
    path = tmp_path / "notice.html"
    path.write_text("<html><body><p>Hello <b>world</b></p></body></html>")
    item = load_document(path, url="https://example.com/n", title="Page")
    assert item.text == "Hello world"


def test_published_date_is_parsed(tmp_path: Path) -> None:
    path = tmp_path / "notice.txt"
    path.write_text("Some text.")
    item = load_document(path, url="https://example.com/n", title="T", published="2026-11-09")
    assert item.published is not None
    assert item.published.year == 2026
    assert item.published.tzinfo is not None


def test_bad_published_date_is_rejected() -> None:
    with pytest.raises(DocumentError, match="published"):
        parse_published("last week")


def test_http_url_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "notice.txt"
    path.write_text("Some text.")
    with pytest.raises(DocumentError, match="https"):
        load_document(path, url="http://example.com/n", title="T")


def test_empty_title_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "notice.txt"
    path.write_text("Some text.")
    with pytest.raises(DocumentError, match="title"):
        load_document(path, url="https://example.com/n", title="   ")


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(DocumentError, match="not found"):
        load_document(tmp_path / "nope.txt", url="https://example.com/n", title="T")


def test_empty_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "notice.txt"
    path.write_text("   \n\n")
    with pytest.raises(DocumentError, match="no text"):
        load_document(path, url="https://example.com/n", title="T")
