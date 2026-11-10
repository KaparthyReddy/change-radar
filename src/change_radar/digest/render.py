"""Render verified alerts as a Markdown or HTML digest."""

from __future__ import annotations

import html
from collections.abc import Sequence
from datetime import date

from change_radar.models import Alert, Item

Entry = tuple[Item, Alert]

DISCLAIMER = (
    "Summaries are machine-written. The only thing checked automatically is that the quoted "
    "passage appears word for word in the source. Always read the quote and the original "
    "notice. This digest reports changes in public documents and is not legal, financial "
    "or compliance advice."
)

_CSS = (
    ":root{--bg:#fff;--fg:#1a1a1a;--muted:#5c5c5c;--rule:#d9d9d9;--accent:#0b5cad}"
    "@media (prefers-color-scheme:dark){"
    ":root{--bg:#141414;--fg:#ececec;--muted:#a0a0a0;--rule:#333;--accent:#6cb0ff}}"
    "body{background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif;margin:0}"
    "main{max-width:46rem;margin:0 auto;padding:2rem 1rem}"
    "article{border-top:1px solid var(--rule);padding-top:1rem;margin-top:1.5rem}"
    "dl{display:grid;grid-template-columns:max-content 1fr;gap:.25rem 1rem}"
    "dt{color:var(--muted)}dd{margin:0}"
    "blockquote{margin:1rem 0;padding-left:1rem;border-left:3px solid var(--rule)}"
    "a{color:var(--accent)}small{color:var(--muted)}"
)


def _line(text: str) -> str:
    return " ".join(text.split())


def _count(number: int) -> str:
    return f"{number} item" + ("" if number == 1 else "s")


def _link(url: str) -> str:
    safe = html.escape(url, quote=True)
    if url.startswith(("https://", "http://")):
        return f'<a href="{safe}" rel="noopener noreferrer">{safe}</a>'
    return safe


def render_markdown(entries: Sequence[Entry], *, title: str, generated: date) -> str:
    """Render the digest as Markdown."""
    lines = [
        f"# {_line(title)}",
        "",
        f"Generated {generated.isoformat()}. {_count(len(entries))}.",
        "",
    ]
    if not entries:
        lines += ["No items.", ""]
    for item, alert in entries:
        lines += [
            f"## {_line(item.title)}",
            "",
            f"- **What changed:** {_line(alert.what_changed)}",
            f"- **Who it affects:** {_line(alert.who_it_affects)}",
            f"- **Deadline:** {_line(alert.deadline)}",
            f"- **What to check:** {_line(alert.what_to_check)}",
            f"- **Source:** <{item.url}> ({_line(item.source_id)})",
            "",
            f'> "{_line(alert.quote)}"',
            "",
        ]
    lines += ["---", "", DISCLAIMER, ""]
    return "\n".join(lines)


def render_html(entries: Sequence[Entry], *, title: str, generated: date) -> str:
    """Render the digest as a single self-contained HTML page. All text is escaped."""
    esc = html.escape
    heading = esc(_line(title))
    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{heading}</title>",
        f"<style>{_CSS}</style>",
        "</head>",
        "<body>",
        "<main>",
        f"<h1>{heading}</h1>",
        f"<p><small>Generated {generated.isoformat()}. {_count(len(entries))}.</small></p>",
    ]
    if not entries:
        parts.append("<p>No items.</p>")
    for item, alert in entries:
        parts += [
            "<article>",
            f"<h2>{esc(_line(item.title))}</h2>",
            "<dl>",
            f"<dt>What changed</dt><dd>{esc(_line(alert.what_changed))}</dd>",
            f"<dt>Who it affects</dt><dd>{esc(_line(alert.who_it_affects))}</dd>",
            f"<dt>Deadline</dt><dd>{esc(_line(alert.deadline))}</dd>",
            f"<dt>What to check</dt><dd>{esc(_line(alert.what_to_check))}</dd>",
            f"<dt>Source</dt><dd>{_link(item.url)} ({esc(_line(item.source_id))})</dd>",
            "</dl>",
            f"<blockquote>{esc(_line(alert.quote))}</blockquote>",
            "</article>",
        ]
    parts += [
        f"<footer><p><small>{esc(DISCLAIMER)}</small></p></footer>",
        "</main>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts) + "\n"
