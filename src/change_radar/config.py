"""Load and validate the list of official sources from a TOML file."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOWED_KINDS = frozenset({"rss"})


class ConfigError(ValueError):
    """Raised when the sources file is invalid."""


@dataclass(frozen=True, slots=True)
class Source:
    """One official source and what we know about its terms of use."""

    id: str
    name: str
    kind: str
    url: str
    terms_url: str = ""
    terms_checked: bool = False
    notes: str = ""


def _require_str(entry: dict[str, Any], field: str, index: int) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(
            f"source #{index}: '{field}' is required and must be a non-empty string"
        )
    return value.strip()


def _parse_entry(entry: dict[str, Any], index: int) -> Source:
    source_id = _require_str(entry, "id", index)
    name = _require_str(entry, "name", index)
    kind = _require_str(entry, "kind", index)
    if kind not in ALLOWED_KINDS:
        raise ConfigError(f"source '{source_id}': kind must be one of {sorted(ALLOWED_KINDS)}")
    url = _require_str(entry, "url", index)
    if not url.startswith("https://"):
        raise ConfigError(f"source '{source_id}': url must start with https://")
    terms_checked = entry.get("terms_checked", False)
    if not isinstance(terms_checked, bool):
        raise ConfigError(f"source '{source_id}': terms_checked must be true or false")
    terms_url = str(entry.get("terms_url", "")).strip()
    if terms_checked and not terms_url:
        raise ConfigError(f"source '{source_id}': terms_checked is true but terms_url is empty")
    return Source(
        id=source_id,
        name=name,
        kind=kind,
        url=url,
        terms_url=terms_url,
        terms_checked=terms_checked,
        notes=str(entry.get("notes", "")).strip(),
    )


def parse_sources(data: dict[str, Any]) -> list[Source]:
    """Turn parsed TOML into validated Source objects."""
    entries = data.get("source")
    if not isinstance(entries, list) or not entries:
        raise ConfigError("no [[source]] entries found")
    sources: list[Source] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ConfigError(f"source #{index}: must be a table")
        source = _parse_entry(entry, index)
        if source.id in seen:
            raise ConfigError(f"duplicate source id: {source.id}")
        seen.add(source.id)
        sources.append(source)
    return sources


def load_sources(path: Path) -> list[Source]:
    """Read and validate a sources TOML file."""
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(f"sources file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc
    return parse_sources(data)


def fetchable(sources: list[Source], include_unchecked: bool = False) -> list[Source]:
    """Sources whose terms have been checked, or all of them if explicitly requested."""
    if include_unchecked:
        return list(sources)
    return [source for source in sources if source.terms_checked]
