"""Pick the extractor: rules alone, or a local model with the rules as a safety net."""

from __future__ import annotations

from change_radar.extract.llm import OllamaExtractor
from change_radar.extract.pipeline import ExtractionResult, Extractor, run_extractor
from change_radar.extract.rules import RuleExtractor
from change_radar.models import Item


def extract_with_fallback(
    item: Item,
    model: str | None = None,
    *,
    llm: Extractor | None = None,
) -> ExtractionResult:
    """Use the model first if one is given. If it yields no verified alert, use the rules."""
    rules = RuleExtractor()
    if llm is None and model is None:
        return run_extractor(rules, item)
    model_extractor: Extractor = llm if llm is not None else OllamaExtractor(model or "")
    first = run_extractor(model_extractor, item)
    if first.accepted:
        return first
    second = run_extractor(rules, item)
    return ExtractionResult(
        accepted=second.accepted,
        rejected=[*first.rejected, *second.rejected],
    )
