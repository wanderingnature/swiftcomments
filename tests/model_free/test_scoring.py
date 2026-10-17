"""The model-free reading, scripts/model_free/, on real text and a real
temporary file: the rules on sentences that carry each dimension, the roll-up
and the rating, the score run end to end over the schema (the class A
population, the five mf_* tables, one transaction, a second run writes
nothing, --comment-id rescoring), and make score-model-compare's pieces that
need no model server: the code stamp, the even pick, the rules' half (JSON
files and score_compare_reading rows, the mf_* tables untouched), the comments
of an earlier run, and the comparison.

    uv run pytest tests/model_free
"""
import io
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))  # the package is imported as run.py imports it

from shared import db, score_json  # noqa: E402
from model_free import RULESET_VERSION, run as mf_run  # noqa: E402
from model_free.arithmetic import rate, roll_up  # noqa: E402
from model_free.detectors import Context  # noqa: E402
from model_free.text import PhraseMatcher, normalize, quoted_spans  # noqa: E402
import score_model_compare  # noqa: E402

GAP_SENTENCE = ("The DEIS fails to analyze sediment delivery to bull trout habitat in Wilson Creek,"
                " so its conclusion of no significant impact cannot stand.")
LAW_SENTENCE = "The proposal violates 36 CFR 294.12."
ASK_SENTENCE = "Please prepare a cumulative effects analysis of sediment delivery before the final EIS."
STAND_SENTENCE = "As a hydrologist I have measured turbidity in the Nantahala National Forest for decades."
ALT_SENTENCE = "Instead, adopt an alternative that keeps a 300 foot buffer along perennial streams."
EVID_SENTENCE = "According to the DEIS, 44.7 million acres would be opened to road construction."
DISPOSITION = "I strongly oppose this rule."


def _one(sentence):
    scores, comment, answer = mf_run.score_text("t", sentence, Context())
    assert len(scores) == 1
    return scores[0], comment, answer


def test_text_tools():
    assert normalize("A &amp; B<br>C  “q”") == 'A & B C "q"'
    q = quoted_spans('The draft says "the effects would be negligible" (USDA 2025) and more.')
    assert len(q) == 1 and q[0].text.startswith('"the effects')
    m = PhraseMatcher(["bull trout", "trout"]).find("Bull trout and brook trout.")
    assert [(x.phrase, x.start, x.end) for x in m] == [("bull trout", 0, 10), ("trout", 21, 26)]


def test_each_dimension_fires_on_its_sentence():
    s, comment, answer = _one(GAP_SENTENCE)
    assert s.dims["GAP"] == 3 and s.dims["PLACE"] == 3 and s.dims["DOC"] == 1
    rules = {h.rule for h in s.hits}
    assert {"GAP.2.specific_name", "GAP.3.stated_consequence", "PLACE.list.3",
            "M2.adequacy_questioned", "M5.missing_analysis_named", "MECH.cause_effect"} <= rules
    assert comment.gate and answer.level == "A2"

    s, comment, answer = _one(LAW_SENTENCE)
    assert s.dims["LAW"] == 2 and s.dims["EVID"] == 0
    assert "LAW.2.citation_form" in {h.rule for h in s.hits}
    assert answer.level == "A1"

    s, _, _ = _one(ASK_SENTENCE)
    assert s.dims["ASK"] == 3 and s.ask_names and s.dims["GAP"] == 2

    s, comment, answer = _one(STAND_SENTENCE)
    assert s.dims["STAND"] == 3 and s.stand_this_place and s.dims["PLACE"] == 1
    assert not comment.gate and answer.level == "A0"

    s, _, _ = _one(ALT_SENTENCE)
    assert s.dims["ALT"] == 2 and s.alt_distinct

    s, _, _ = _one(EVID_SENTENCE)
    assert s.dims["EVID"] == 3 and s.evid_applied

    # A sentence under 25 letters and digits is not a unit (stored_units drops
    # it); the whole comment still reads it.
    with pytest.raises(ValueError, match="no sentences"):
        mf_run.score_text("t", DISPOSITION, Context())
    scores, comment, _ = mf_run.score_text("t", DISPOSITION, Context(), "whole")
    assert [s.unit_id for s in scores] == [-1]
    assert comment.strength == 1 and comment.band == "minimal" and not comment.gate


def test_roll_up_takes_the_maximum_and_names_the_first_sentence():
    scores, _, _ = mf_run.score_text("t", GAP_SENTENCE + " " + DISPOSITION + " " + LAW_SENTENCE, Context())
    # the short disposition joins no neighbour and is dropped: two units
    assert len(scores) == 2
    comment = roll_up("t", scores)
    assert comment.dims["GAP"] == 3 and comment.dims["LAW"] == 2 and comment.sentence_count == 2
    assert {b["dimension"]: b["unit_id"] for b in comment.gate_basis} == {"GAP": 1, "LAW": 2}
    assert rate(comment).level == "A1"


def test_a_comment_with_no_sentence_has_no_units():
    from model_free import inputs
    assert inputs.comment_units(7, "c", DISPOSITION) is None
    sentences, whole = inputs.comment_units(7, "c", GAP_SENTENCE + " " + LAW_SENTENCE)
    assert [u.unit_id for u in sentences] == [700001, 700002] and whole.unit_id == -700001
    assert sentences[1].text == LAW_SENTENCE and whole.start_char == 0


CIDS = ["FS-2025-0001-0001", "FS-2025-0001-0002", "FS-2025-0001-0003"]


@pytest.fixture
def dbfile(tmp_path, monkeypatch):
    path = tmp_path / "roadless.sqlite"
    conn = db.connect(path, create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    texts = [GAP_SENTENCE + " " + LAW_SENTENCE, EVID_SENTENCE, GAP_SENTENCE]
    for cid, text in zip(CIDS, texts):
        conn.execute("INSERT INTO comment (comment_id, comment_text) VALUES (?, ?)", (cid, text))
        conn.execute("INSERT INTO substance_floor (comment_id, floored, has_entity, has_citation,"
                     " has_deficiency, has_firstperson) VALUES (?, 0, 1, 0, 1, 0)", (cid,))
    # Two class A rows and one B1: the population is class A unless asked.
    conn.execute("INSERT INTO substance_screen (comment_id, screen_class, authority, reference, doc_cite,"
                 " action_ref, deficiency, evid_ner) VALUES (?, 'A', 1, 0, 0, 1, 1, 0)", (CIDS[0],))
    conn.execute("INSERT INTO substance_screen (comment_id, screen_class, authority, reference, doc_cite,"
                 " action_ref, deficiency, evid_ner) VALUES (?, 'A', 0, 0, 1, 1, 0, 0)", (CIDS[1],))
    conn.execute("INSERT INTO substance_screen (comment_id, screen_class, authority, reference, doc_cite,"
                 " action_ref, deficiency, evid_ner) VALUES (?, 'B1', 0, 0, 0, 1, 0, 1)", (CIDS[2],))
    conn.execute("INSERT INTO comment_authorities (comment_id, citation, mode, matched_text, family_key)"
                 " VALUES (?, '36 CFR 294', 'strict', '36 CFR 294.12', '36 cfr 294')", (CIDS[0],))
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", path)
    return path


def test_score_run_reads_the_classes_asked_for(dbfile, capsys):
    # B1 alone: the one B1 comment, whose GAP opens the gate; class A untouched.
    assert mf_run.main(["score", "--classes", "B1"]) == 0
    assert "1 class B1 comments; 0 scored under rule set" in capsys.readouterr().out
    conn = db.connect(dbfile)
    assert [tuple(r) for r in conn.execute("SELECT comment_id, gate FROM mf_comment_score")] == [(CIDS[2], 1)]
    conn.close()
    # A and B1 together: the B1 comment is already scored, the two A comments are not.
    assert mf_run.main(["score", "--classes", "A,B1"]) == 0
    assert "3 class A/B1 comments; 1 scored under rule set" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="no class B2 comment"):
        mf_run.main(["score", "--classes", "B2"])


def test_score_run_over_the_file(dbfile, capsys):
    assert mf_run.main(["score", "--limit", "1"]) == 0
    out = capsys.readouterr().out
    assert "2 class A comments; 0 scored under rule set" in out and "1 to score" in out
    conn = db.connect(dbfile)
    assert [r[0] for r in conn.execute("SELECT comment_id FROM mf_comment_score")] == [CIDS[0]]
    row = conn.execute("SELECT gap, law, gate, band, run_id FROM mf_comment_score").fetchone()
    assert (row["gap"], row["law"], row["gate"], row["band"]) == (3, 2, 1, "marginal")
    assert conn.execute("SELECT level FROM mf_comment_answerability").fetchone()[0] == "A1"
    # Hybrid: the two sentences and the whole comment, each a unit.
    rowid = conn.execute("SELECT rowid FROM comment WHERE comment_id = ?", (CIDS[0],)).fetchone()[0]
    units = [tuple(r) for r in conn.execute(
        "SELECT unit_id, start_char FROM mf_sentence_score ORDER BY unit_id")]
    assert units == [(-(rowid * 100000 + 1), 0), (rowid * 100000 + 1, 0),
                     (rowid * 100000 + 2, len(GAP_SENTENCE) + 1)]
    # LAW's authority is found in its sentence and in the whole comment
    assert conn.execute("SELECT count(*) FROM mf_sentence_hit WHERE rule = 'LAW.2.confirmed_authority'").fetchone()[0] == 2
    run = conn.execute("SELECT comments_scored, units_scored, finished_at FROM mf_score_run").fetchone()
    assert (run["comments_scored"], run["units_scored"]) == (1, 3) and run["finished_at"]
    conn.close()

    # The rest of the population, then nothing left.
    assert mf_run.main(["score"]) == 0
    assert "1 scored under rule set" in capsys.readouterr().out
    assert mf_run.main(["score"]) == 0
    assert "nothing to score" in capsys.readouterr().out
    conn = db.connect(dbfile)
    assert conn.execute("SELECT count(*) FROM mf_comment_score").fetchone()[0] == 2
    assert conn.execute("SELECT count(*) FROM mf_score_run").fetchone()[0] == 2
    # Rescoring a named comment replaces its rows with the same values.
    before = conn.execute("SELECT * FROM mf_comment_score WHERE comment_id = ?", (CIDS[1],)).fetchone()
    conn.close()
    assert mf_run.main(["score", "--comment-id", CIDS[1]]) == 0
    conn = db.connect(dbfile)
    after = conn.execute("SELECT * FROM mf_comment_score WHERE comment_id = ?", (CIDS[1],)).fetchone()
    assert tuple(after)[3:] == tuple(before)[3:] and after["run_id"] != before["run_id"]
    assert conn.execute("SELECT count(*) FROM mf_sentence_hit").fetchone()[0] == \
        conn.execute("SELECT count(*) FROM mf_sentence_hit WHERE run_id IN"
                     " (SELECT run_id FROM mf_sentence_score)").fetchone()[0]
    conn.close()
    assert mf_run.main(["report"]) == 0
    assert '"comments": 2' in capsys.readouterr().out


def _compare_run(conn, run_id, comments_of=None):
    conn.execute("INSERT INTO score_compare_run (run_id, started_at, code_version, code_dirty, model,"
                 " server, instrument_version, ruleset_version, comments_of, pool, picked)"
                 " VALUES (?, '2026-10-16T00:00:00+00:00', 'abc', 0, 'm', 'http://x', 'v3', ?, ?, 2, 2)",
                 (run_id, RULESET_VERSION, comments_of))
    conn.commit()


def test_compare_rules_half_keeps_its_readings_apart(dbfile, tmp_path):
    out_dir = tmp_path / "model-free"
    conn = db.connect(dbfile)
    _compare_run(conn, "r1")
    rec = score_model_compare.rules_reading(conn, "r1", {CIDS[0], CIDS[1]}, out_dir)
    assert sorted(rec) == CIDS[:2] and sorted(score_json.read_dir(out_dir)) == CIDS[:2]
    assert rec[CIDS[0]]["scorer"] == "rules" and rec[CIDS[0]]["instrument"] == f"rules-{RULESET_VERSION}"
    assert rec[CIDS[0]]["levels"]["GAP"] == 3 and rec[CIDS[0]]["a_level"] == "A1"
    rows = conn.execute("SELECT comment_id, method, record, error FROM score_compare_reading"
                        " ORDER BY comment_id").fetchall()
    assert [(r["comment_id"], r["method"], r["error"]) for r in rows] == \
        [(CIDS[0], "model-free", None), (CIDS[1], "model-free", None)]
    assert score_json.check(__import__("json").loads(rows[0]["record"]))["levels"]["GAP"] == 3
    # The scoring step's own tables are not the comparison's.
    assert conn.execute("SELECT count(*) FROM mf_comment_score").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM mf_score_run").fetchone()[0] == 0
    # A later run reads the same comments again.
    assert score_model_compare.comments_of(conn, "r1") == CIDS[:2]
    with pytest.raises(SystemExit, match="no comparison run r9"):
        score_model_compare.comments_of(conn, "r9")
    conn.close()


def test_compare_stamps_the_commit():
    head, dirty = score_model_compare.code_version()
    assert len(head) == 40 and dirty in (0, 1)


def test_compare_picks_at_even_steps():
    ids = [f"c{i:02d}" for i in range(10)]
    assert score_model_compare.pick(list(reversed(ids)), 3) == ["c00", "c03", "c06"]
    assert score_model_compare.pick(ids, 10) == ids
    with pytest.raises(SystemExit, match="more than the 10"):
        score_model_compare.pick(ids, 11)


def test_score_run_needs_the_screen(tmp_path, monkeypatch):
    path = tmp_path / "roadless.sqlite"
    conn = db.connect(path, create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", path)
    with pytest.raises(SystemExit, match="run make screen first"):
        mf_run.main(["score"])


def _record(cid, scorer, levels, a_level="A0", evidence=()):
    strength = sum(levels.values())
    return {"comment_id": cid, "scorer": scorer, "instrument": "v3" if scorer == "model" else "rules-3",
            "model": "m" if scorer == "model" else None, "levels": levels, "strength": strength,
            "gate": any(levels[d] >= 2 for d in ("GAP", "EVID", "ALT", "LAW")), "gate_basis": [],
            "band": "minimal" if strength <= 5 else "marginal", "a_level": a_level, "evidence": list(evidence)}


def test_score_json_check_and_compare(tmp_path):
    zero = {d: 0 for d in score_json.DIMS}
    bad = _record("x", "rules", zero)
    bad["strength"] = 4
    with pytest.raises(ValueError, match="not the sum"):
        score_json.check(bad)
    a_dir, b_dir = tmp_path / "a", tmp_path / "b"
    score_json.write(a_dir, _record("c1", "model", {**zero, "GAP": 2}, "A3",
                                    [{"dimension": "GAP", "quote": "fails to analyze"}]))
    score_json.write(a_dir, _record("c2", "model", {**zero, "LAW": 2}, "A1"))
    score_json.write(b_dir, _record("c1", "rules", {**zero, "GAP": 2}, "A3",
                                    [{"dimension": "GAP", "grade": 2, "rule": "GAP.2.specific_name",
                                      "match": "bull trout", "start": 0, "end": 10}]))
    score_json.write(b_dir, _record("c2", "rules", zero, "A0",
                                    [{"dimension": "GAP", "grade": 0, "rule": "GAP.0.nothing_named",
                                      "match": "fails to", "start": 0, "end": 8}]))
    score_json.write(b_dir, _record("c3", "rules", zero, "A0"))
    out = io.StringIO()
    assert score_json.compare(score_json.read_dir(a_dir), score_json.read_dir(b_dir), 20, out,
                              labels=("model", "rules")) == 0
    text = out.getvalue()
    assert "both read 2; only model 0; only rules 1" in text
    assert "GAP           2             0             0" in text
    assert "LAW           1             1             0" in text
    assert "gate      same on 1 of 2; open: model 2, rules 1, both 1" in text
    assert "level     same on 1 of 2 rated on both sides" in text
    assert "comments that differ: 1 on the gate, 0 more on a level" in text
    # Only the differing comment is laid out, dimension by dimension, each side's
    # evidence under the dimension it belongs to.
    assert "\nc2\n  gate      model: open    rules: closed" in text
    assert "  * LAW    model 2  rules 0" in text
    assert '      rules  GAP.0.nothing_named: "fails to"' in text
    assert "GAP.2.specific_name" not in text
