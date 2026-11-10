from change_radar.fetch.text import html_to_text


def test_strips_tags_and_separates_blocks() -> None:
    assert html_to_text("<p>Hello <b>world</b></p><p>Second&nbsp;line</p>") == (
        "Hello world\nSecond line"
    )


def test_drops_scripts_and_styles() -> None:
    assert html_to_text("<script>alert(1)</script><style>p{}</style><p>Text</p>") == "Text"


def test_decodes_entities() -> None:
    assert html_to_text("<p>Fees &amp; charges</p>") == "Fees & charges"


def test_empty_input() -> None:
    assert html_to_text("") == ""
