from change_radar.extract.rules import RuleExtractor, find_dates, is_relevant, split_sentences
from change_radar.models import Item
from change_radar.verify import verify_alert

TEXT = (
    "The regulator has reviewed the position. "
    "On a review, it has been decided to extend the timeline for tokenisation of "
    "card-on-file data by three months, to September 30, 2022. "
    "All payment aggregators and merchants must delete stored card data by that date. "
    "Entities may contact the department for queries."
)


def make_item(
    text: str = TEXT, title: str = "Card-on-file tokenisation: timeline extended"
) -> Item:
    return Item(source_id="rbi", url="https://example.com/n1", title=title, text=text)


def test_picks_the_sentence_that_states_the_change() -> None:
    item = make_item()
    alerts = RuleExtractor()(item)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.quote.startswith("On a review, it has been decided to extend")
    assert alert.deadline == "September 30, 2022"
    assert alert.what_changed == item.title
    assert alert.source_url == item.url
    assert "payment aggregators" in alert.who_it_affects
    assert "merchants" in alert.who_it_affects
    assert verify_alert(alert, item).ok


def test_irrelevant_notice_gives_no_alert() -> None:
    item = make_item(
        text="The Bank has published the holiday calendar. Offices will close on public holidays.",
        title="Holiday calendar",
    )
    assert not is_relevant(item)
    assert RuleExtractor()(item) == []


def test_relevant_notice_without_a_change_cue_gives_no_alert() -> None:
    item = make_item(text="The payment system continues to operate normally across all channels.")
    assert is_relevant(item)
    assert RuleExtractor()(item) == []


def test_deadline_is_none_stated_when_the_sentence_has_no_date() -> None:
    item = make_item(
        text="All payment aggregators must delete stored card data without delay and report back."
    )
    alerts = RuleExtractor()(item)
    assert len(alerts) == 1
    assert alerts[0].deadline == "none stated"


def test_find_dates() -> None:
    assert find_dates("by 30 September 2022 and again on Oct 1, 2022") == [
        "30 September 2022",
        "Oct 1, 2022",
    ]
    assert find_dates("from 1st October 2022.") == ["1st October 2022"]
    assert find_dates("no dates here") == []


def test_split_sentences() -> None:
    assert split_sentences("One two three four five.   Six seven eight nine ten.") == [
        "One two three four five.",
        "Six seven eight nine ten.",
    ]
