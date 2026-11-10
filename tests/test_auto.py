from change_radar.extract.auto import extract_with_fallback
from change_radar.extract.pipeline import ExtractionError
from change_radar.models import Alert, Item

TEXT = "All payment aggregators must delete stored card data by September 30, 2022."
ITEM = Item(source_id="rbi", url="https://example.com/n1", title="Card data rule", text=TEXT)


def model_alert() -> Alert:
    return Alert(
        item_key=ITEM.key,
        what_changed="Aggregators must delete stored card data.",
        who_it_affects="Payment aggregators",
        deadline="September 30, 2022",
        what_to_check="Check your card storage",
        quote="All payment aggregators must delete stored card data",
        source_url=ITEM.url,
    )


def test_rules_are_used_when_no_model_is_given() -> None:
    result = extract_with_fallback(ITEM)
    assert len(result.accepted) == 1
    assert result.accepted[0].what_changed == "Card data rule"


def test_model_result_is_used_when_it_verifies() -> None:
    alert = model_alert()
    result = extract_with_fallback(ITEM, "any-model", llm=lambda item: [alert])
    assert result.accepted == [alert]


def test_rules_are_the_safety_net_when_the_model_finds_nothing() -> None:
    result = extract_with_fallback(ITEM, "any-model", llm=lambda item: [])
    assert len(result.accepted) == 1
    assert result.accepted[0].what_changed == "Card data rule"


def test_rules_are_the_safety_net_when_the_model_fails() -> None:
    def failing(item: Item) -> list[Alert]:
        raise ExtractionError("model unavailable")

    result = extract_with_fallback(ITEM, "any-model", llm=failing)
    assert len(result.accepted) == 1
    assert [rejection.reason for rejection in result.rejected] == ["model unavailable"]
