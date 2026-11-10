"""Deterministic verification. The model is never trusted to check its own output."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from change_radar.models import NO_DEADLINE, Alert, Item

MIN_QUOTE_WORDS = 5

_TRANSLATE = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u00ad": "",
    }
)


@dataclass(frozen=True, slots=True)
class QuoteCheck:
    """Result of a verification: ok, or not ok with the reason."""

    ok: bool
    reason: str = ""


def normalise(text: str) -> str:
    """Ignore typography and whitespace differences; keep the words and their case."""
    text = unicodedata.normalize("NFKC", text).translate(_TRANSLATE)
    return " ".join(text.split())


def verify_quote(quote: str, source_text: str, min_words: int = MIN_QUOTE_WORDS) -> QuoteCheck:
    """Check that the quote is a contiguous, word-for-word excerpt of the source text."""
    normalised_quote = normalise(quote)
    if not normalised_quote:
        return QuoteCheck(False, "quote is empty")
    if "..." in normalised_quote:
        return QuoteCheck(False, "quote contains an ellipsis; quotes must be contiguous")
    if len(normalised_quote.split()) < min_words:
        return QuoteCheck(False, f"quote has fewer than {min_words} words")
    if normalised_quote not in normalise(source_text):
        return QuoteCheck(False, "quote not found in source text")
    return QuoteCheck(True)


def verify_deadline(deadline: str, source_text: str) -> QuoteCheck:
    """A stated deadline must appear word for word in the source text."""
    value = normalise(deadline)
    if not value or value.lower() == NO_DEADLINE:
        return QuoteCheck(True)
    if value not in normalise(source_text):
        return QuoteCheck(False, "deadline not found in source text")
    return QuoteCheck(True)


def verify_alert(alert: Alert, item: Item) -> QuoteCheck:
    """Check that an alert belongs to the item, links to it, and quotes it accurately."""
    if alert.item_key != item.key:
        return QuoteCheck(False, "alert does not belong to this item")
    if alert.source_url != item.url:
        return QuoteCheck(False, "alert source_url does not match the item URL")
    quote = verify_quote(alert.quote, item.text)
    if not quote.ok:
        return quote
    return verify_deadline(alert.deadline, item.text)
