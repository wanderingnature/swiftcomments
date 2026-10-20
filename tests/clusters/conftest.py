"""The case fixture of the clustering tests: six groups of sentences in two
families, made from fixed points, and a few strays, in a real temporary file
with their occurrences, a sentence build and their vectors."""
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

from shared import db, embeddings  # noqa: E402
from clusters import analysis  # noqa: E402
from clusters.embed import VIEWS, pack  # noqa: E402

# Two families, three groups each; the family word is in every sentence of it.
GROUPS = [("wildfire", "ignition", "EVID"), ("wildfire", "smoke", "EVID"), ("wildfire", "fuel", "LAW"),
          ("water", "sediment", "GAP"), ("water", "trout", "GAP"), ("water", "intake", "LAW")]
PER_GROUP = 25
STRAYS = 8


def _vectors():
    rng = np.random.default_rng(7)
    fams = analysis.unit(rng.normal(size=(2, embeddings.DIMENSIONS)))
    out = []
    for g, (fam, _, _) in enumerate(GROUPS):
        f = fams[0 if fam == "wildfire" else 1]
        centre = analysis.unit((f + 0.45 * analysis.unit(rng.normal(size=(1, embeddings.DIMENSIONS)))[0])[None])[0]
        out.append(analysis.unit(centre + 0.012 * rng.normal(size=(PER_GROUP, embeddings.DIMENSIONS))))
    strays = analysis.unit(rng.normal(size=(STRAYS, embeddings.DIMENSIONS)))
    return out, strays


@pytest.fixture
def casefile(tmp_path, monkeypatch):
    path = tmp_path / "roadless.sqlite"
    conn = db.connect(path, create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    groups, strays = _vectors()
    sent, occ, emb = [], [], []
    unit_id = 1
    for g, (fam, word, kind) in enumerate(GROUPS):
        for i in range(PER_GROUP):
            key = f"g{g}s{i:02d}"
            text = f"The {fam} {word} concern number {i} about the {fam} {word} in the forest."
            flags = {k: int(k == kind) for k in ("LAW", "EVID", "GAP", "ALT")}
            # the last two of each group only hold a whole-comment hit; the rest open the gate
            opens, holds = (0, 1) if i >= PER_GROUP - 2 else (1, 0)
            sent.append((key, text, 1, 1, flags["LAW"], flags["EVID"], flags["GAP"], flags["ALT"], opens, holds))
            occ.append((unit_id, key, f"c{g}-{i:02d}", flags["LAW"], flags["EVID"], flags["GAP"], flags["ALT"],
                        opens, holds))
            unit_id += 1
            emb.append((key, groups[g][i]))
    for i in range(STRAYS):
        key = f"stray{i}"
        sent.append((key, f"An unrelated remark number {i} on nothing.", 1, 1, 0, 1, 0, 0, 1, 0))
        occ.append((unit_id, key, f"cs-{i}", 0, 1, 0, 0, 1, 0))
        unit_id += 1
        emb.append((key, strays[i]))
    conn.executemany("INSERT INTO gate_sentence VALUES (?,?,?,?,?,?,?,?,?,?)", sent)
    conn.executemany("INSERT INTO gate_sentence_occurrence VALUES (?,?,?,?,?,?,?,?,?)", occ)
    conn.execute("INSERT INTO gate_sentence_run (ruleset_version, classes, created_at, gate_comments, occurrences,"
                 " distinct_sentences, comments_opening, comments_hit, comments_neither, sentences_unlocated,"
                 " hits_unlocated) VALUES ('3', 'A,B1', '2026-10-20', ?, ?, ?, 0, 0, 0, 0, 0)",
                 (len(occ), len(occ), len(sent)))
    conn.executemany("INSERT INTO sentence_embedding VALUES (?, 'm', ?, 'x', 1024, ?, '2026-10-20')",
                     [(k, VIEWS["comment"], pack(v)) for k, v in emb])
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", path)
    return path


