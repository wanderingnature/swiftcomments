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
    # The system prompt is one paragraph, shown as a quoted block so it wraps; the
    # user template keeps its line breaks and indentation in a fenced block.
    quoted = [line[2:] for line in page.splitlines() if line.startswith("> ")]
    assert quoted == [row["system_prompt"]]
    blocks = _fenced(page)
    assert len(blocks) == 1, "the page holds the user template fenced, once"
    assert blocks[0] == row["user_prompt_template"]
    assert f"`{row['prompt_name']}`" in page
    assert f"the {n_topics} active" in page
    assert page.startswith("# This is the prompt for step 3, the stance (`make stance`)")
    assert "\n# System prompt\n" in page and "\n# User template\n" in page


def test_substance_and_roster_instruments_are_where_the_scripts_read_them():
    """The substance schema is the bare JSON schema the scorer loads as
    RUBRIC_SCHEMA; the roster's is a response_format envelope whose "schema" the
    roster script takes out."""
    scoring = json.loads((INSTRUMENTS / "substantive-scoring-v3.schema.json").read_text(encoding="utf-8"))
    assert scoring["type"] == "object" and "evidence" in scoring["properties"]
    roster = json.loads((INSTRUMENTS / "organisation-roster-v1.schema.json").read_text(encoding="utf-8"))
    assert roster["name"] == "organisation_roster_v1" and roster["schema"]["type"] == "object"

    # Each file opens with its step label; the prompt is the text after the marker,
    # and for the substance instrument before SECTION D (plan 5.2 edit 13). The
    # scripts find both markers by first occurrence, so the labels must not contain
    # them: the slices below are taken the same way.
    # The prompt is a quoted block (every line starts with ">"), as the stance page
    # shows its prompt; the scripts strip one quote mark per line before sending.
    marker = "\n# System prompt\n"
    text = (INSTRUMENTS / "substantive-scoring-v3.md").read_text(encoding="utf-8")
    assert text.startswith("# This is the prompt for step 6, the substance reading (`make score-model`)")
    start, end = text.index(marker), text.index("# SECTION D")
    assert start < end
    prompt = _unquoted(text[start + len(marker):end])
    assert prompt.startswith("You read one public comment on a federal agency action.")
    assert "# SECTION C" in prompt
    text = (INSTRUMENTS / "organisation-roster-v1.md").read_text(encoding="utf-8")
    assert text.startswith("# This is the prompt for step 8, the roster (`make attachments`)")
    assert _unquoted(text[text.index(marker) + len(marker):]).startswith("You are reading the opening")


def _unquoted(block):
    """The prompt text of a quoted block: one '> ' (or a bare '>') off every line.
    Every non-blank line of the block has to carry it, or a line of the prompt
    would render outside the quote."""
    lines = block.strip("\n").split("\n")
    for line in lines:
        assert line == "" or line.startswith(">"), line
    return "\n".join(line[2:] if line.startswith("> ") else line[1:] if line.startswith(">") else line
                     for line in lines).strip()
