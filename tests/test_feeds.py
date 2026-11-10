import pytest

from change_radar.config import Source
from change_radar.fetch.feeds import FeedError, fetch_feed, parse_feed

SOURCE = Source(id="test-feed", name="Test feed", kind="rss", url="https://example.com/feed.xml")

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Feed</title>
<item><title>Notice one</title><link>https://example.com/one</link>
<description>&lt;p&gt;The regulator has extended the deadline.&lt;/p&gt;</description>
<pubDate>Mon, 09 Nov 2026 10:00:00 GMT</pubDate></item>
<item><title>No link</title><description>skip me</description></item>
<item><title>Notice one again</title><link>https://example.com/one</link>
<description>duplicate</description></item>
<item><title>Title only</title><link>https://example.com/two</link></item>
</channel></rss>"""

ATOM_FEED = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Atom feed</title>
<entry><title>Atom notice</title>
<link href="https://example.com/atom-1" rel="alternate"/>
<updated>2026-11-09T10:00:00Z</updated>
<summary>Summary text here.</summary></entry>
</feed>"""


def test_parses_rss_and_removes_duplicates() -> None:
    items = parse_feed(RSS, SOURCE)
    assert [item.title for item in items] == ["Notice one", "Title only"]
    first = items[0]
    assert first.source_id == "test-feed"
    assert first.url == "https://example.com/one"
    assert first.text == "The regulator has extended the deadline."
    assert first.published is not None
    assert first.published.year == 2026
    assert first.published.tzinfo is not None


def test_uses_title_when_there_is_no_description() -> None:
    items = parse_feed(RSS, SOURCE)
    assert items[1].text == "Title only"


def test_parses_atom() -> None:
    items = parse_feed(ATOM_FEED, SOURCE)
    assert len(items) == 1
    assert items[0].url == "https://example.com/atom-1"
    assert items[0].text == "Summary text here."
    assert items[0].published is not None


def test_invalid_xml_is_rejected() -> None:
    with pytest.raises(FeedError, match="valid XML"):
        parse_feed(b"this is not xml", SOURCE)


def test_xml_entities_are_refused() -> None:
    bad = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><rss><channel/></rss>'
    with pytest.raises(FeedError, match="entities"):
        parse_feed(bad, SOURCE)


def test_fetch_feed_uses_the_given_fetcher() -> None:
    requested: list[str] = []

    def fetcher(url: str) -> bytes:
        requested.append(url)
        return RSS

    assert len(fetch_feed(SOURCE, fetcher)) == 2
    assert requested == [SOURCE.url]
