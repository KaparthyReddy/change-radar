"""Rule-based extraction: deterministic, no model, no network.

Produces a plain triage alert from an item. The quote is a sentence taken from the item's
own text. The deadline is a date found in that same sentence, or "none stated". Groups are
listed only if the notice names them.
"""

from __future__ import annotations

import re

from change_radar.models import NO_DEADLINE, Alert, Item
from change_radar.verify import MIN_QUOTE_WORDS, normalise

MAX_QUOTE_WORDS = 60
WHAT_TO_CHECK = "Read the quoted passage and the full notice to see whether it applies to you."
NOT_IDENTIFIED = "Not identified automatically; read the notice."

_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
    "|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec"
)
_DATE = re.compile(
    rf"\b(?:\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS})\.?,?\s+\d{{4}}"
    rf"|(?:{_MONTHS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}})\b",
    re.IGNORECASE,
)

_RELEVANCE_TERMS = (
    r"payments?", r"upi", r"cards?", r"tokeni[sz]\w*", r"kyc", r"digital lending",
    r"nbfcs?", r"aggregators?", r"wallets?", r"prepaid", r"merchants?", r"cyber",
    r"outsourcing", r"fintech", r"authentication", r"e-?mandates?", r"data localisation",
)
_RELEVANT = re.compile(r"\b(?:" + "|".join(_RELEVANCE_TERMS) + r")\b", re.IGNORECASE)

_CUES = re.compile(
    r"\b(?:extend\w*|extension|deadline|with effect from|effective|not later than|shall|must"
    r"|required to|mandatory|revis\w*|amend\w*|withdraw\w*|discontinu\w*|prohibit\w*)\b",
    re.IGNORECASE,
)

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(])")

_ENTITIES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bpayment aggregators?\b", re.IGNORECASE), "payment aggregators"),
    (re.compile(r"\bpayment system operators?\b", re.IGNORECASE), "payment system operators"),
    (
        re.compile(r"\bprepaid payment instruments?\b", re.IGNORECASE),
        "prepaid payment instrument issuers",
    ),
    (re.compile(r"\bcard (?:issuers?|networks?)\b", re.IGNORECASE), "card issuers and networks"),
    (re.compile(r"\bNBFCs?\b"), "NBFCs"),
    (re.compile(r"\bbanks\b", re.IGNORECASE), "banks"),
    (re.compile(r"\bmerchants?\b", re.IGNORECASE), "merchants"),
    (re.compile(r"\bregulated entities\b", re.IGNORECASE), "regulated entities"),
)


def find_dates(text: str) -> list[str]:
    """Dates written out in full, such as '30 September 2022' or 'Oct 1, 2022'."""
    return [match.group(0) for match in _DATE.finditer(text)]


def split_sentences(text: str) -> list[str]:
    """Split text into sentences. Whitespace is normalised first."""
    flat = normalise(text)
    return [sentence.strip() for sentence in _SENTENCE_BREAK.split(flat) if sentence.strip()]


def is_relevant(item: Item) -> bool:
    """True if the item mentions payments or fintech topics at all."""
    return _RELEVANT.search(f"{item.title} {item.text}") is not None


def affected_groups(text: str) -> str:
    """Describe the groups the notice names, without claiming they are affected."""
    found = [label for pattern, label in _ENTITIES if pattern.search(text)]
    if not found:
        return NOT_IDENTIFIED
    return "Entities named in the notice: " + ", ".join(found[:4]) + "."


def _usable(sentence: str) -> bool:
    return MIN_QUOTE_WORDS <= len(sentence.split()) <= MAX_QUOTE_WORDS


class RuleExtractor:
    """Deterministic extractor. Quotes are sentences copied from the item's own text."""

    def __call__(self, item: Item) -> list[Alert]:
        if not is_relevant(item):
            return []
        best: str | None = None
        best_score = 0
        for sentence in split_sentences(item.text):
            if not _usable(sentence):
                continue
            cues = len(_CUES.findall(sentence))
            if cues == 0:
                continue
            score = 2 * min(cues, 3)
            score += 1 if find_dates(sentence) else 0
            score += 1 if _RELEVANT.search(sentence) else 0
            if score > best_score:
                best, best_score = sentence, score
        if best is None:
            return []
        dates = find_dates(best)
        return [
            Alert(
                item_key=item.key,
                what_changed=normalise(item.title),
                who_it_affects=affected_groups(item.text),
                deadline=dates[0] if dates else NO_DEADLINE,
                what_to_check=WHAT_TO_CHECK,
                quote=best,
                source_url=item.url,
            )
        ]
