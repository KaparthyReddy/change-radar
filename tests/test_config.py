from pathlib import Path

import pytest

from change_radar.config import ConfigError, fetchable, load_sources

VALID = """
[[source]]
id = "first"
name = "First"
kind = "rss"
url = "https://example.com/feed.xml"
terms_url = "https://example.com/terms"
terms_checked = true

[[source]]
id = "second"
name = "Second"
kind = "rss"
url = "https://example.com/other.xml"
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "sources.toml"
    path.write_text(text)
    return path


def test_loads_valid_file(tmp_path: Path) -> None:
    sources = load_sources(write(tmp_path, VALID))
    assert [s.id for s in sources] == ["first", "second"]
    assert sources[0].terms_checked
    assert not sources[1].terms_checked


def test_fetchable_skips_unchecked_by_default(tmp_path: Path) -> None:
    sources = load_sources(write(tmp_path, VALID))
    assert [s.id for s in fetchable(sources)] == ["first"]


def test_fetchable_can_include_unchecked(tmp_path: Path) -> None:
    sources = load_sources(write(tmp_path, VALID))
    assert len(fetchable(sources, include_unchecked=True)) == 2


def test_duplicate_ids_are_rejected(tmp_path: Path) -> None:
    text = VALID.replace('id = "second"', 'id = "first"')
    with pytest.raises(ConfigError, match="duplicate"):
        load_sources(write(tmp_path, text))


def test_missing_field_is_rejected(tmp_path: Path) -> None:
    text = VALID.replace('name = "Second"\n', "")
    with pytest.raises(ConfigError, match="name"):
        load_sources(write(tmp_path, text))


def test_checked_terms_need_a_terms_url(tmp_path: Path) -> None:
    text = VALID.replace('terms_url = "https://example.com/terms"\n', "")
    with pytest.raises(ConfigError, match="terms_url"):
        load_sources(write(tmp_path, text))


def test_non_https_url_is_rejected(tmp_path: Path) -> None:
    text = VALID.replace("https://example.com/other.xml", "http://example.com/other.xml")
    with pytest.raises(ConfigError, match="https"):
        load_sources(write(tmp_path, text))


def test_unknown_kind_is_rejected(tmp_path: Path) -> None:
    text = VALID.replace('kind = "rss"', 'kind = "scrape"', 1)
    with pytest.raises(ConfigError, match="kind"):
        load_sources(write(tmp_path, text))


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_sources(tmp_path / "nope.toml")


def test_invalid_toml_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="invalid TOML"):
        load_sources(write(tmp_path, "this is = = not toml"))


def test_file_without_sources_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="no"):
        load_sources(write(tmp_path, 'title = "empty"'))


def test_bundled_sources_file_is_valid() -> None:
    path = Path(__file__).resolve().parent.parent / "sources" / "sources.toml"
    assert load_sources(path)
