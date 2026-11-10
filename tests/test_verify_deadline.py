from change_radar.models import Alert, Item
from change_radar.verify import verify_alert, verify_deadline

TEXT = "The regulator has extended the deadline to September 30, 2022 for all merchants."
ITEM = Item(source_id="rbi", url="https://example.com/n1", title="Notice", text=TEXT)
QUOTE = "The regulator has extended the deadline to September 30, 2022"


def make_alert(deadline: str) -> Alert:
    return Alert(
        item_key=ITEM.key,
        what_changed="Deadline extended",
        who_it_affects="Merchants",
        deadline=deadline,
        what_to_check="Check your plan",
        quote=QUOTE,
        source_url=ITEM.url,
    )


def test_deadline_found_in_the_text_passes() -> None:
    assert verify_deadline("September 30, 2022", TEXT).ok


def test_none_stated_and_empty_pass() -> None:
    assert verify_deadline("none stated", TEXT).ok
    assert verify_deadline("None stated", TEXT).ok
    assert verify_deadline("", TEXT).ok


def test_deadline_not_in_the_text_fails() -> None:
    result = verify_deadline("30 September 2022", TEXT)
    assert not result.ok
    assert "deadline not found" in result.reason


def test_alert_with_an_invented_deadline_fails() -> None:
    result = verify_alert(make_alert("31 December 2030"), ITEM)
    assert not result.ok
    assert "deadline" in result.reason


def test_alert_with_a_real_deadline_passes() -> None:
    assert verify_alert(make_alert("September 30, 2022"), ITEM).ok
