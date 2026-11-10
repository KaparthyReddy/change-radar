from dataclasses import replace

from change_radar.extract.pipeline import ExtractionError, run_extractor
from change_radar.models import Alert, Item

TEXT = "The regulator has decided to extend the deadline for tokenisation by three months."
ITEM = Item(source_id="rbi", url="https://example.com/n1", title="Notice", text=TEXT)
GOOD = "has decided to extend the deadline for tokenisation"
INVENTED = "The regulator has cancelled the deadline for tokenisation entirely"


def make_alert(quote: str) -> Alert:
    return Alert(
        item_key=ITEM.key,
        what_changed="Deadline extended",
        who_it_affects="Merchants",
        deadline="none stated",
        what_to_check="Check your plan",
        quote=quote,
        source_url=ITEM.url,
    )


def test_verified_alert_is_accepted() -> None:
    alert = make_alert(GOOD)
    result = run_extractor(lambda item: [alert], ITEM)
    assert result.accepted == [alert]
    assert result.rejected == []


def test_invented_quote_is_rejected() -> None:
    result = run_extractor(lambda item: [make_alert(INVENTED)], ITEM)
    assert result.accepted == []
    assert "not found" in result.rejected[0].reason


def test_wrong_link_is_rejected() -> None:
    wrong = replace(make_alert(GOOD), source_url="https://example.com/other")
    result = run_extractor(lambda item: [wrong], ITEM)
    assert result.accepted == []
    assert "source_url" in result.rejected[0].reason


def test_duplicate_quotes_are_kept_once() -> None:
    alert = make_alert(GOOD)
    result = run_extractor(lambda item: [alert, alert], ITEM)
    assert len(result.accepted) == 1
    assert result.rejected[0].reason == "duplicate quote"


def test_good_and_bad_alerts_are_separated() -> None:
    good = make_alert(GOOD)
    bad = make_alert(INVENTED)
    result = run_extractor(lambda item: [bad, good], ITEM)
    assert result.accepted == [good]
    assert len(result.rejected) == 1


def test_extractor_error_becomes_a_rejection() -> None:
    def failing(item: Item) -> list[Alert]:
        raise ExtractionError("model unavailable")

    result = run_extractor(failing, ITEM)
    assert result.accepted == []
    assert result.rejected[0].reason == "model unavailable"
    assert result.rejected[0].alert is None


def test_no_candidates_gives_an_empty_result() -> None:
    result = run_extractor(lambda item: [], ITEM)
    assert result.accepted == []
    assert result.rejected == []
