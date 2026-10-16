"""The one comment sentence method against stored comments and their expected units
(tests/fixtures/comment_sentences.json)."""
import json
from pathlib import Path

import pytest

from comment_sentences import stored_units

CASES = json.loads((Path(__file__).parent / "fixtures" / "comment_sentences.json").read_text())["cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["case"] for c in CASES])
def test_stored_units_match_the_fixture(case):
    got = [[a, b, t] for a, b, t, _ in stored_units(case["text"])[0]]
    assert got == case["units"]
