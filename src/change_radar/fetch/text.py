"""Turn HTML, or feed descriptions that contain HTML, into plain text."""

from __future__ import annotations

from html.parser import HTMLParser

_BLOCK_TAGS = frozenset(
    {
        "p", "div", "br", "li", "tr", "table", "ul", "ol", "section", "article",
        "h1", "h2", "h3", "h4", "h5", "h6",
    }
)
_SKIP_TAGS = frozenset({"script", "style"})


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def html_to_text(markup: str) -> str:
    """Strip tags, drop scripts and styles, and collapse whitespace line by line."""
    extractor = _TextExtractor()
    extractor.feed(markup)
    extractor.close()
    lines = [" ".join(line.split()) for line in extractor.text().splitlines()]
    return "\n".join(line for line in lines if line)
