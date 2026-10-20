"""Step 10, the sentences of the gate set (scripts/clusters/sentences.py), on
real comments scored by the real model-free reading in a temporary file: the
gate set by class, the occurrences and the distinct sentences, the sentence
that opens the gate alone, the sentence that holds a whole-comment gate hit,
the location of sentences in the whole text, and the stops.

    uv run pytest tests/clusters
"""
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

from shared import db  # noqa: E402
from model_free import run as mf_run  # noqa: E402
from clusters import sentences  # noqa: E402

GAP_SENTENCE = ("The DEIS fails to analyze sediment delivery to bull trout habitat in Wilson Creek,"
                " so its conclusion of no significant impact cannot stand.")
LAW_SENTENCE = "The proposal violates 36 CFR 294.12."
STAND_SENTENCE = "As a hydrologist I have measured turbidity in the Nantahala National Forest for decades."
# No sentence of it opens the gate alone; the whole comment opens it on EVID ("data" in the first).
WHOLE_FIRST = "According to the agency's own data for this forest."
WHOLE_SECOND = "Roads are found near many towns in the Pisgah National Forest."

CIDS = {"a_two": "FS-2025-0001-0001", "b1_whole": "FS-2025-0001-0002", "a_copy": "FS-2025-0001-0003",
        "b2": "FS-2025-0001-0004", "a_closed": "FS-2025-0001-0005"}
TEXTS = {"a_two": GAP_SENTENCE + " " + LAW_SENTENCE, "b1_whole": WHOLE_FIRST + " " + WHOLE_SECOND,
         "a_copy": GAP_SENTENCE, "b2": GAP_SENTENCE + " " + LAW_SENTENCE, "a_closed": STAND_SENTENCE}
# authority, action_ref, deficiency, evid_ner: each class as the screen derives it
SCREEN_FLAGS = {"A": (1, 1, 1, 0), "B1": (0, 1, 0, 1), "B2": (0, 0, 0, 0)}
CLASSES = {"a_two": "A", "b1_whole": "B1", "a_copy": "A", "b2": "B2", "a_closed": "A"}


@pytest.fixture
def scored(tmp_path, monkeypatch):
    path = tmp_path / "roadless.sqlite"
    conn = db.connect(path, create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    for name, cid in CIDS.items():
        conn.execute("INSERT INTO comment (comment_id, comment_text) VALUES (?, ?)", (cid, TEXTS[name]))
        conn.execute("INSERT INTO substance_screen (comment_id, screen_class, authority, reference, doc_cite,"
                     " action_ref, deficiency, evid_ner) VALUES (?, ?, ?, 0, 0, ?, ?, ?)",
                     (cid, CLASSES[name], *SCREEN_FLAGS[CLASSES[name]]))
    conn.execute("INSERT INTO comment_authorities (comment_id, citation, mode, matched_text, family_key)"
                 " VALUES (?, '36 CFR 294', 'strict', '36 CFR 294.12', '36 cfr 294')", (CIDS["a_two"],))
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", path)
    assert mf_run.main(["score", "--classes", "A,B1,B2"]) == 0
    return path


def test_locate_on_letters_and_digits():
    whole = 'He said “roads & fire”.  Then   more. Last one'
    spans = sentences.locate(whole, ['He said "roads & fire".', "Then more.", "Not here at all", "Last one"])
    assert spans[0] == (0, whole.index("”")) and whole[spans[1][0]:spans[1][1]] == "Then   more"
    assert spans[2] is None and whole[spans[3][0]:spans[3][1]] == "Last one"


def test_build_writes_the_gate_set(scored, capsys):
    assert sentences.main([]) == 0
    out = capsys.readouterr().out
    assert "class A: 3 comments, 3 with a model-free score under rule set" in out
    assert "class B1: 1 comments" in out and "class B2" not in out
    conn = db.connect(scored)
    run = conn.execute("SELECT * FROM gate_sentence_run").fetchone()
    # The closed A comment and the B2 comment are not in the gate set.
    assert (run["classes"], run["gate_comments"], run["occurrences"], run["distinct_sentences"]) == ("A,B1", 3, 5, 4)
    # The two-sentence A comment opens on LAW from the whole comment as well, so its LAW sentence holds a hit.
    assert (run["comments_opening"], run["comments_hit"], run["comments_neither"]) == (2, 2, 0)
    assert (run["sentences_unlocated"], run["hits_unlocated"]) == (0, 0)
    rows = {r["text"]: r for r in conn.execute("SELECT * FROM gate_sentence")}
    gap = rows[GAP_SENTENCE]
    assert (gap["occurrences"], gap["comments"], gap["gap"], gap["opens"]) == (2, 2, 1, 1)
    # The B1 comment: no sentence opens the gate alone; the first holds the whole comment's EVID hit.
    assert (rows[LAW_SENTENCE]["law"], rows[LAW_SENTENCE]["holds_hit"]) == (1, 1)
    first, second = rows[WHOLE_FIRST], rows[WHOLE_SECOND]
    assert (first["opens"], first["holds_hit"], second["opens"], second["holds_hit"]) == (0, 1, 0, 0)
    assert conn.execute("SELECT count(DISTINCT comment_id) FROM gate_sentence_occurrence WHERE comment_id = ?",
                        (CIDS["b2"],)).fetchone()[0] == 0
    # A rebuild replaces the rows and keeps a second run row.
    conn.close()
    assert sentences.main(["--classes", "A"]) == 0
    conn = db.connect(scored)
    assert conn.execute("SELECT count(*) FROM gate_sentence_run").fetchone()[0] == 2
    assert conn.execute("SELECT count(*) FROM gate_sentence_occurrence").fetchone()[0] == 3
    assert WHOLE_FIRST not in {r[0] for r in conn.execute("SELECT text FROM gate_sentence")}
    conn.close()


def test_a_changed_text_stops_the_step(scored):
    conn = db.connect(scored)
    conn.execute("UPDATE comment SET comment_text = ? WHERE comment_id = ?",
                 (GAP_SENTENCE.replace("bull trout", "brook trout"), CIDS["a_copy"]))
    conn.commit()
    conn.close()
    with pytest.raises(SystemExit, match="not the sentence that was scored"):
        sentences.main([])


def test_no_scores_stops_the_step(tmp_path, monkeypatch):
    path = tmp_path / "roadless.sqlite"
    conn = db.connect(path, create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", path)
    with pytest.raises(SystemExit, match="run make score-model-free first"):
        sentences.main([])
