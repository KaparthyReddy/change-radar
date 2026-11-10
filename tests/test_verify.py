from dataclasses import replace

from change_radar.models import Alert, Item
from change_radar.verify import normalise, verify_alert, verify_quote

SOURCE = "The regulator has decided to extend the deadline for tokenisation by three months."


def make_item(text: str = SOURCE) -> Item:
    return Item(source_id="rbi", url="https://example.com/a", title="Notice", text=text)


def make_alert(item: Item, quote: str) -> Alert:
    return Alert(
        item_key=item.key,
        what_changed="Deadline extended",
        who_it_affects="Merchants",
        deadline="none stated",
        what_to_check="Whether the new date affects your plan",
        quote=quote,
        source_url=item.url,
    )


def test_exact_quote_passes() -> None:
    assert verify_quote("has decided to extend the deadline for tokenisation", SOURCE).ok


def test_whitespace_and_typography_are_ignored() -> None:
    source = (
        "The regulator\nhas   decided to extend the deadline for "
        "\u2018tokenisation\u2019 by three."
    )
    quote = "The regulator has decided to extend the deadline for 'tokenisation' by three."
    assert verify_quote(quote, source).ok


def test_paraphrase_fails() -> None:
    quote = "The regulator postponed the tokenisation deadline by three months"
    result = verify_quote(quote, SOURCE)
    assert not result.ok
    assert "not found" in result.reason


def test_case_matters() -> None:
    assert not verify_quote("the regulator has decided to extend the deadline", SOURCE).ok


def test_short_quote_fails() -> None:
    result = verify_quote("extend the deadline", SOURCE)
    assert not result.ok
    assert "fewer than" in result.reason


def test_ellipsis_fails() -> None:
    result = verify_quote("The regulator has decided ... by three months.", SOURCE)
    assert not result.ok
    assert "ellipsis" in result.reason


def test_empty_quote_fails() -> None:
    assert not verify_quote("   ", SOURCE).ok


def test_normalise_collapses_whitespace() -> None:
    assert normalise("a \n b\t c") == "a b c"


def test_alert_with_valid_quote_passes() -> None:
    item = make_item()
    alert = make_alert(item, "has decided to extend the deadline for tokenisation")
    assert verify_alert(alert, item).ok


def test_alert_for_another_item_fails() -> None:
    item = make_item()
    other = Item(source_id="rbi", url="https://example.com/other", title="x", text=SOURCE)
    alert = make_alert(other, "has decided to extend the deadline for tokenisation")
    assert not verify_alert(alert, item).ok


def test_alert_with_wrong_link_fails() -> None:
    item = make_item()
    alert = make_alert(item, "has decided to extend the deadline for tokenisation")
    wrong = replace(alert, source_url="https://example.com/wrong")
    result = verify_alert(wrong, item)
    assert not result.ok
    assert "source_url" in result.reason
