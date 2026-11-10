import json
from typing import Any

import pytest

from change_radar.extract.llm import MAX_TEXT_CHARS, OllamaExtractor, PostJson, parse_reply
from change_radar.extract.pipeline import ExtractionError, run_extractor
from change_radar.models import Item

TEXT = (
    "The regulator has decided to extend the timeline for tokenisation by three months. "
    "All merchants must delete stored card data by the new date."
)
QUOTE = "The regulator has decided to extend the timeline for tokenisation by three months."
ITEM = Item(source_id="rbi", url="https://example.com/n1", title="Tokenisation timeline", text=TEXT)
GOOD_ENTRY = {
    "what_changed": "The tokenisation deadline was extended by three months.",
    "who_it_affects": "Merchants",
    "deadline": "none stated",
    "what_to_check": "Check your card storage plan.",
    "quote": QUOTE,
}


def make_post(
    content: str | dict[str, Any], captured: list[dict[str, Any]] | None = None
) -> PostJson:
    def post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        if captured is not None:
            captured.append(payload)
        text = content if isinstance(content, str) else json.dumps(content)
        return {"message": {"content": text}}

    return post


def reply_with(entries: list[Any]) -> dict[str, Any]:
    return {"message": {"content": json.dumps({"alerts": entries})}}


def test_valid_reply_becomes_alerts() -> None:
    extractor = OllamaExtractor("test-model", post=make_post({"alerts": [GOOD_ENTRY]}))
    alerts = extractor(ITEM)
    assert len(alerts) == 1
    assert alerts[0].item_key == ITEM.key
    assert alerts[0].source_url == ITEM.url
    assert alerts[0].quote == QUOTE


def test_missing_optional_fields_get_defaults() -> None:
    entry = {"what_changed": "Something changed.", "quote": QUOTE}
    alerts = parse_reply(reply_with([entry]), ITEM)
    assert alerts[0].deadline == "none stated"
    assert alerts[0].who_it_affects == "Not stated"


def test_entries_without_a_quote_are_skipped() -> None:
    alerts = parse_reply(reply_with([{"what_changed": "x"}, "junk", GOOD_ENTRY]), ITEM)
    assert len(alerts) == 1


def test_no_more_than_three_alerts_are_taken() -> None:
    assert len(parse_reply(reply_with([GOOD_ENTRY] * 5), ITEM)) == 3


def test_invalid_json_is_an_extraction_error() -> None:
    extractor = OllamaExtractor("test-model", post=make_post("this is not json"))
    with pytest.raises(ExtractionError, match="not valid JSON"):
        extractor(ITEM)


def test_reply_without_content_is_an_extraction_error() -> None:
    extractor = OllamaExtractor("test-model", post=lambda url, payload: {})
    with pytest.raises(ExtractionError, match="no message content"):
        extractor(ITEM)


def test_alerts_that_are_not_a_list_are_an_extraction_error() -> None:
    extractor = OllamaExtractor("test-model", post=make_post({"alerts": "none"}))
    with pytest.raises(ExtractionError, match="alerts"):
        extractor(ITEM)


def test_invented_quote_is_rejected_by_the_gate() -> None:
    quote = "The regulator has cancelled the tokenisation deadline completely."
    bad = dict(GOOD_ENTRY, quote=quote)
    extractor = OllamaExtractor("test-model", post=make_post({"alerts": [bad]}))
    result = run_extractor(extractor, ITEM)
    assert result.accepted == []
    assert "not found" in result.rejected[0].reason


def test_request_is_built_safely() -> None:
    captured: list[dict[str, Any]] = []
    extractor = OllamaExtractor("test-model", post=make_post({"alerts": []}, captured))
    assert extractor(ITEM) == []
    payload = captured[0]
    assert payload["model"] == "test-model"
    assert payload["stream"] is False
    assert payload["format"] == "json"
    assert payload["options"]["temperature"] == 0
    system, user = payload["messages"]
    assert system["role"] == "system"
    assert TEXT not in system["content"]
    assert TEXT in user["content"]


def test_long_text_is_truncated() -> None:
    captured: list[dict[str, Any]] = []
    extractor = OllamaExtractor("test-model", post=make_post({"alerts": []}, captured))
    long_item = Item(
        source_id="rbi",
        url="https://example.com/long",
        title="Long",
        text="x" * (MAX_TEXT_CHARS + 500),
    )
    extractor(long_item)
    assert "x" * (MAX_TEXT_CHARS + 1) not in captured[0]["messages"][1]["content"]


def test_model_server_must_be_local() -> None:
    with pytest.raises(ValueError, match="localhost"):
        OllamaExtractor("test-model", base_url="http://example.com:11434")


def test_model_name_is_required() -> None:
    with pytest.raises(ValueError, match="model"):
        OllamaExtractor("   ")
