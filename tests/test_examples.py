from pathlib import Path

from change_radar.extract import run_extractor
from change_radar.extract.rules import RuleExtractor
from change_radar.importer import load_document

DEMO = Path(__file__).resolve().parent.parent / "examples" / "demo-notice.txt"


def test_demo_notice_produces_one_verified_alert() -> None:
    item = load_document(DEMO, url="https://example.com/demo", title="Demo notice")
    result = run_extractor(RuleExtractor(), item)
    assert len(result.accepted) == 1
    assert result.accepted[0].deadline == "September 30, 2022"
    assert result.rejected == []
