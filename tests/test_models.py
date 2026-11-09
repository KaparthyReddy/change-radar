from change_radar.models import Item


def make_item(source_id: str = "rbi", url: str = "https://example.com/a") -> Item:
    return Item(source_id=source_id, url=url, title="Notice", text="Some text.")


def test_key_is_stable() -> None:
    assert make_item().key == make_item().key


def test_key_depends_on_url_and_source() -> None:
    base = make_item()
    assert base.key != make_item(url="https://example.com/b").key
    assert base.key != make_item(source_id="npci").key


def test_key_has_expected_length() -> None:
    assert len(make_item().key) == 16
