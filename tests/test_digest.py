from datetime import date

from change_radar.digest.render import render_html, render_markdown
from change_radar.models import Alert, Item

ITEM = Item(
    source_id="rbi",
    url="https://example.com/n1",
    title="Card <data> rule",
    text="The regulator has decided to extend the timeline for tokenisation.",
)
ALERT = Alert(
    item_key=ITEM.key,
    what_changed="Deadline extended",
    who_it_affects="Merchants",
    deadline="none stated",
    what_to_check="Check your plan",
    quote="has decided to extend the timeline for tokenisation",
    source_url=ITEM.url,
)
DAY = date(2026, 11, 9)


def test_markdown_contains_the_essentials() -> None:
    text = render_markdown([(ITEM, ALERT)], title="Test digest", generated=DAY)
    assert "# Test digest" in text
    assert "Generated 2026-11-09. 1 item." in text
    assert "- **What changed:** Deadline extended" in text
    assert '> "has decided to extend the timeline for tokenisation"' in text
    assert "<https://example.com/n1>" in text
    assert "not legal" in text


def test_markdown_with_no_entries() -> None:
    text = render_markdown([], title="Empty", generated=DAY)
    assert "0 items" in text
    assert "No items." in text


def test_html_escapes_text() -> None:
    text = render_html([(ITEM, ALERT)], title="Test <digest>", generated=DAY)
    assert "Card &lt;data&gt; rule" in text
    assert "<data>" not in text
    assert "Test &lt;digest&gt;" in text
    assert 'href="https://example.com/n1"' in text
    assert text.startswith("<!doctype html>")


def test_html_does_not_link_unsafe_urls() -> None:
    unsafe = Item(source_id="x", url="javascript:alert(1)", title="T", text="Some text here.")
    alert = Alert(
        item_key=unsafe.key,
        what_changed="x",
        who_it_affects="y",
        deadline="none stated",
        what_to_check="z",
        quote="Some text here",
        source_url=unsafe.url,
    )
    text = render_html([(unsafe, alert)], title="T", generated=DAY)
    assert "<a href" not in text
