"""The copy hashes strip the submission form's markup and entities before
comparing (rtca defect 7): the exact hash of comments_db/src/preprocessing/
text_processor.py and the body hash of comments_db/scripts/
deduplicate_middle_content.py, each over one letter written with and without
the form's markup. Before the fix '<br/>' hashed as the word 'br' and '&amp;'
as 'amp', and the body window was cut over the markup.

The middle-content script imports comments_db's `src`; the repo's top-level
`src` shares the name, so the script is loaded by path with that entry set
aside for the test (monkeypatch restores it).

    uv run pytest tests/test_copy_hashes.py
"""
import importlib.util
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

import comments_db.src.preprocessing.text_processor as tp  # noqa: E402

PLAIN = ("Keep the Roadless Rule. It protects clean water & wildlife. " * 12
         + "Thank you for reading this letter.")
MARKED = ("Keep the Roadless Rule.<br/>It protects clean water &amp; wildlife.<br/><br/>" * 12
          + "<span style='padding-left: 30px'>Thank you for reading this letter.</span>")


def test_exact_hash_ignores_the_forms_markup():
    proc = tp.TextProcessor()
    assert proc.get_hashes(MARKED) == proc.get_hashes(PLAIN)
    assert "br" not in proc.get_canonical_text("Keep it.<br/>Thanks").split()
    assert "amp" not in proc.get_canonical_text("water &amp; wildlife").split()
    assert proc.get_hashes("Keep the rule.") != proc.get_hashes("Keep the rule. Please.")


@pytest.fixture
def middle(monkeypatch):
    for name in [m for m in sys.modules if m == "src" or m.startswith("src.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.syspath_prepend(str(_REPO / "comments_db"))
    spec = importlib.util.spec_from_file_location(
        "deduplicate_middle_content",
        _REPO / "comments_db" / "scripts" / "deduplicate_middle_content.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_body_hash_cuts_the_window_after_the_markup_is_gone(middle):
    dedup = middle.MiddleContentDeduplicator(ctx=None, chars=60, mode="trim-end", dry_run=True)
    _, plain_hash = dedup.get_middle_hash(PLAIN)
    _, marked_hash = dedup.get_middle_hash(MARKED)
    assert plain_hash is not None
    assert marked_hash == plain_hash
    _, other = dedup.get_middle_hash(PLAIN.replace("clean water", "old growth"))
    assert other != plain_hash
    assert dedup.get_middle_hash("") == (None, None)
