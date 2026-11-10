"""Run an extractor and keep only alerts whose quotes verify. No quote, no alert."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from change_radar.models import Alert, Item
from change_radar.verify import normalise, verify_alert

Extractor = Callable[[Item], list[Alert]]


class ExtractionError(Exception):
    """Raised by an extractor when it cannot produce a usable answer."""


@dataclass(frozen=True, slots=True)
class Rejection:
    """An alert, or a failure, that did not make it through."""

    reason: str
    alert: Alert | None = None


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """Alerts that passed verification, and everything that was turned away."""

    accepted: list[Alert] = field(default_factory=list)
    rejected: list[Rejection] = field(default_factory=list)


def run_extractor(extractor: Extractor, item: Item) -> ExtractionResult:
    """Extract candidate alerts from one item and verify each of them."""
    try:
        candidates = extractor(item)
    except ExtractionError as exc:
        return ExtractionResult(rejected=[Rejection(str(exc))])
    accepted: list[Alert] = []
    rejected: list[Rejection] = []
    seen: set[str] = set()
    for alert in candidates:
        check = verify_alert(alert, item)
        quote_key = normalise(alert.quote)
        if not check.ok:
            rejected.append(Rejection(check.reason, alert))
        elif quote_key in seen:
            rejected.append(Rejection("duplicate quote", alert))
        else:
            seen.add(quote_key)
            accepted.append(alert)
    return ExtractionResult(accepted=accepted, rejected=rejected)
