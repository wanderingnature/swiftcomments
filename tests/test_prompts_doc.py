"""The prompt pages agree with what the model is sent.

docs/instruments/stance-roadless-rescission-v2.md is a copy of the active stance
prompt for reading; the seeds are the source. The test loads the seeds into a
temporary file as make schema does and compares the page's two fenced blocks with
the active prompt row. The substance and roster instruments are the files the
scripts read, so they need no copy; the test checks they are where the scripts
look and that each schema file parses.

    uv run pytest tests/test_prompts_doc.py
"""
import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from shared import db  # noqa: E402

INSTRUMENTS = _REPO / "docs" / "instruments"
STANCE_PAGE = INSTRUMENTS / "stance-roadless-rescission-v2.md"


def _fenced(text):
    return re.findall(r"^```\n(.*?)\n```$", text, re.S | re.M)


def test_stance_page_is_the_seeded_prompt(tmp_path):
    conn = db.connect(tmp_path / "roadless.sqlite", create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    for name in ("roadless_profile.sql", "roadless_prompt_v2.sql"):
        conn.executescript((_REPO / "seeds" / name).read_text(encoding="utf-8"))
    row = conn.execute("SELECT prompt_name, system_prompt, user_prompt_template FROM prompts"
                       " WHERE prompt_kind = 'sentiment_topic' AND is_active").fetchone()
    n_topics = conn.execute("SELECT count(*) FROM topics WHERE is_active").fetchone()[0]
    conn.close()
    page = STANCE_PAGE.read_text(encoding="utf-8")
    blocks = _fenced(page)
    assert len(blocks) == 2, "the page holds the system prompt and the user template, fenced"
    assert blocks[0] == row["system_prompt"]
    assert blocks[1] == row["user_prompt_template"]
    assert f"`{row['prompt_name']}`" in page
    assert f"the {n_topics} active" in page


def test_substance_and_roster_instruments_are_where_the_scripts_read_them():
    for stem in ("substantive-scoring-v3", "organisation-roster-v1"):
        text = (INSTRUMENTS / f"{stem}.md").read_text(encoding="utf-8")
        schema = json.loads((INSTRUMENTS / f"{stem}.schema.json").read_text(encoding="utf-8"))
        assert schema["schema"]["type"] == "object"
        assert text.strip()
    assert "# SECTION D" in (INSTRUMENTS / "substantive-scoring-v3.md").read_text(encoding="utf-8")
    assert "## System prompt" in (INSTRUMENTS / "organisation-roster-v1.md").read_text(encoding="utf-8")
