"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from change_radar import __version__
from change_radar.config import ConfigError, fetchable, load_sources
from change_radar.digest.render import render_html, render_markdown
from change_radar.extract.auto import extract_with_fallback
from change_radar.fetch.feeds import FeedError, fetch_feed
from change_radar.fetch.http import FetchError, PoliteFetcher
from change_radar.importer import DocumentError, load_document
from change_radar.models import Alert, Item
from change_radar.store import Store
from change_radar.verify import verify_alert

DEFAULT_DB = "data/radar.sqlite"
DEFAULT_SOURCES = "sources/sources.toml"


def _error(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def _add_db(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", default=DEFAULT_DB, help="path to the SQLite database")


def _add_sources(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--sources", default=DEFAULT_SOURCES, help="path to the sources file")


def cmd_sources(args: argparse.Namespace) -> int:
    try:
        sources = load_sources(Path(args.sources))
    except ConfigError as exc:
        return _error(str(exc))
    for source in sources:
        status = "terms checked" if source.terms_checked else "TERMS NOT CLEARED"
        print(f"{source.id}: {source.name} [{status}]")
        print(f"  {source.url}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    try:
        sources = load_sources(Path(args.sources))
    except ConfigError as exc:
        return _error(str(exc))
    chosen = fetchable(sources, include_unchecked=args.include_unchecked)
    skipped = len(sources) - len(chosen)
    if skipped:
        print(
            f"skipped {skipped} source(s) whose terms are not cleared "
            "(--include-unchecked is for local development only)"
        )
    if not chosen:
        print("nothing to fetch")
        return 0
    fetcher = PoliteFetcher()
    failures = 0
    with Store(args.db) as store:
        for source in chosen:
            try:
                items = fetch_feed(source, fetcher)
            except (FetchError, FeedError) as exc:
                print(f"{source.id}: FAILED: {exc}", file=sys.stderr)
                failures += 1
                continue
            counts = {"new": 0, "changed": 0, "unchanged": 0}
            for item in items:
                counts[store.upsert_item(item)] += 1
            print(f"{source.id}: {len(items)} items {counts}")
    return 1 if failures else 0


def cmd_import(args: argparse.Namespace) -> int:
    try:
        item = load_document(
            Path(args.file),
            url=args.url,
            title=args.title,
            source_id=args.source_id,
            published=args.published,
        )
    except DocumentError as exc:
        return _error(str(exc))
    with Store(args.db) as store:
        status = store.upsert_item(item)
    print(f"{status}: {item.title} ({item.key})")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    saved = 0
    turned_away = 0
    with Store(args.db) as store:
        for item in store.items():
            if not args.all and store.alerts(item.key):
                continue
            try:
                result = extract_with_fallback(item, args.model)
            except ValueError as exc:
                return _error(str(exc))
            for alert in result.accepted:
                store.add_alert(alert)
            saved += len(result.accepted)
            turned_away += len(result.rejected)
            print(
                f"{item.title}: {len(result.accepted)} accepted, "
                f"{len(result.rejected)} rejected"
            )
            for rejection in result.rejected:
                print(f"  rejected: {rejection.reason}")
    print(f"done: {saved} alerts saved, {turned_away} rejected")
    return 0


def _warn_about_sources(used: set[str], sources_path: Path) -> None:
    try:
        known = {source.id: source for source in load_sources(sources_path)}
    except ConfigError:
        return
    uncleared = sorted(name for name in used if name in known and not known[name].terms_checked)
    unlisted = sorted(name for name in used if name not in known)
    if uncleared:
        print(
            "warning: this digest includes items from sources whose terms are not cleared: "
            + ", ".join(uncleared)
            + ". Do not publish it.",
            file=sys.stderr,
        )
    if unlisted:
        print(
            "note: hand-imported or unlisted sources: "
            + ", ".join(unlisted)
            + ". You are responsible for having permission to use them.",
            file=sys.stderr,
        )


def cmd_digest(args: argparse.Namespace) -> int:
    entries: list[tuple[Item, Alert]] = []
    with Store(args.db) as store:
        for item in store.items():
            for alert in store.alerts(item.key):
                check = verify_alert(alert, item)
                if check.ok:
                    entries.append((item, alert))
                else:
                    print(
                        f"skipped an alert for '{item.title}': {check.reason}",
                        file=sys.stderr,
                    )
    if not entries:
        print("no verified alerts found; import or fetch, then run extract", file=sys.stderr)
    _warn_about_sources({item.source_id for item, _ in entries}, Path(args.sources))
    render = render_html if args.format == "html" else render_markdown
    output = render(entries, title=args.title, generated=datetime.now(UTC).date())
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
        print(f"wrote {path}")
    else:
        print(output)
    return 0


HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "sources": cmd_sources,
    "fetch": cmd_fetch,
    "import": cmd_import,
    "extract": cmd_extract,
    "digest": cmd_digest,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="change-radar",
        description=(
            "Early warning for fintech rule changes, "
            "with every claim quoted from the source."
        ),
    )
    parser.add_argument("--version", action="version", version=f"change-radar {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list sources and their terms status (offline)")
    _add_sources(p_sources)

    p_fetch = sub.add_parser("fetch", help="fetch feeds from sources whose terms are cleared")
    _add_sources(p_fetch)
    _add_db(p_fetch)
    p_fetch.add_argument(
        "--include-unchecked",
        action="store_true",
        help="local development only: also fetch sources whose terms are not cleared",
    )

    p_import = sub.add_parser("import", help="import a document you read by hand")
    p_import.add_argument("file", help="a .txt or .html file with the document's text")
    p_import.add_argument("--url", required=True, help="the page the document came from")
    p_import.add_argument("--title", required=True, help="the document's title")
    p_import.add_argument("--source-id", default="manual", help="a label for the source")
    p_import.add_argument("--published", help="publication date, such as 2026-11-09")
    _add_db(p_import)

    p_extract = sub.add_parser("extract", help="create verified alerts from stored items")
    p_extract.add_argument("--model", help="optional local Ollama model name")
    p_extract.add_argument(
        "--all", action="store_true", help="also process items that already have alerts"
    )
    _add_db(p_extract)

    p_digest = sub.add_parser("digest", help="render a digest from verified alerts")
    p_digest.add_argument("--format", choices=("md", "html"), default="md")
    p_digest.add_argument("--out", help="write to this file instead of the terminal")
    p_digest.add_argument("--title", default="Change Radar digest")
    _add_sources(p_digest)
    _add_db(p_digest)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return HANDLERS[args.command](args)
