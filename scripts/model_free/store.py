"""The package's own tables: five mf_* tables in data/roadless.sqlite, created
by make schema (schema/roadless.sql, section 9b). One write interface.

The connection is shared/db.py's, and the transaction is the caller's (run.py
wraps a run in `with conn.transaction()`, so a run writes all of its rows or
none).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

from .arithmetic import Answerability, CommentScore, band_of, gate_basis, strength_of
from .detectors import SentenceScore

DIM_COLS = ("place", "stand", "doc", "gap", "evid", "ask", "alt", "law")


@dataclass
class Store:
    conn: object

    # ----------------------------------------------------------- reads

    def scored_comment_ids(self, ruleset: str) -> set[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT comment_id FROM mf_comment_score WHERE ruleset_version = ?", (ruleset,))
        return {r[0] for r in rows}

    def scored_unit_ids(self, ruleset: str) -> set[int]:
        rows = self.conn.execute(
            "SELECT unit_id FROM mf_sentence_score WHERE ruleset_version = ?", (ruleset,))
        return {int(r[0]) for r in rows}

    def comment_count(self, ruleset: str) -> int:
        return int(self.conn.execute(
            "SELECT count(*) FROM mf_comment_score WHERE ruleset_version = ?", (ruleset,)).fetchone()[0])

    # ---------------------------------------------------------- writes

    def start_run(self, ruleset: str, started_at: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO mf_score_run (ruleset_version, started_at) VALUES (?, ?)", (ruleset, started_at))
        run_id = cur.lastrowid
        assert run_id is not None
        return int(run_id)

    def finish_run(self, run_id: int, finished_at: str, units: int, comments: int,
                   counts: dict[str, int], checks: dict[str, object]) -> None:
        self.conn.execute(
            "UPDATE mf_score_run SET finished_at = ?, units_scored = ?, comments_scored = ?,"
            " counts_json = ?, checks_json = ? WHERE run_id = ?",
            (finished_at, units, comments, json.dumps(counts, sort_keys=True),
             json.dumps(checks, sort_keys=True), run_id))

    def write_sentences(self, ruleset: str, run_id: int, scores: Iterable[SentenceScore]) -> int:
        rows = []
        hit_rows = []
        n = 0
        for s in scores:
            n += 1
            d = s.dims
            strength = strength_of(d)
            basis = gate_basis(d)
            rows.append((
                ruleset, s.unit_id, run_id, s.comment_id, s.start_char, s.end_char, s.text_key,
                d["PLACE"], d["STAND"], d["DOC"], d["GAP"], d["EVID"], d["ASK"], d["ALT"], d["LAW"],
                strength, int(bool(basis)), json.dumps(basis), band_of(strength),
                json.dumps(s.moves), json.dumps(s.targets),
                int(s.evid_applied), int(s.ask_names), int(s.alt_distinct), int(s.stand_this_place),
                int(s.is_record_text), json.dumps(s.anchors)))
            for h in s.hits:
                hit_rows.append((ruleset, s.unit_id, run_id, h.dimension, h.grade, h.rule,
                                 h.match, h.start, h.end))
        self.conn.executemany(
            "INSERT OR REPLACE INTO mf_sentence_score VALUES (" + ",".join("?" * 27) + ")", rows)
        if hit_rows:
            unit_ids = sorted({r[1] for r in hit_rows})
            self.conn.executemany(
                "DELETE FROM mf_sentence_hit WHERE ruleset_version = ? AND unit_id = ?",
                [(ruleset, u) for u in unit_ids])
            self.conn.executemany(
                "INSERT INTO mf_sentence_hit (ruleset_version, unit_id, run_id, dimension, grade,"
                " rule, match, start_char, end_char) VALUES (?,?,?,?,?,?,?,?,?)", hit_rows)
        return n

    def write_comments(self, ruleset: str, run_id: int,
                       scores: Iterable[tuple[CommentScore, Answerability]]) -> int:
        rows = []
        arows = []
        n = 0
        for c, a in scores:
            n += 1
            d = c.dims
            rows.append((
                ruleset, c.comment_id, run_id,
                d["PLACE"], d["STAND"], d["DOC"], d["GAP"], d["EVID"], d["ASK"], d["ALT"], d["LAW"],
                c.strength, int(c.gate), json.dumps(c.gate_basis), c.band,
                json.dumps(c.moves), json.dumps(c.targets), c.sentence_count))
            arows.append((ruleset, a.comment_id, run_id, a.level, json.dumps(a.defeated),
                          json.dumps(a.open), int(a.mechanism), int(a.cite)))
        self.conn.executemany(
            "INSERT OR REPLACE INTO mf_comment_score VALUES (" + ",".join("?" * 18) + ")", rows)
        self.conn.executemany(
            "INSERT OR REPLACE INTO mf_comment_answerability VALUES (?,?,?,?,?,?,?,?)", arows)
        return n

    # ---------------------------------------------------------- report

    def report(self, ruleset: str) -> dict[str, object]:
        q = self.conn.execute
        out: dict[str, object] = {}
        out["runs"] = [dict(zip(("run_id", "started_at", "finished_at", "units", "comments"), tuple(r)))
                       for r in q("SELECT run_id, started_at, finished_at, units_scored,"
                                  " comments_scored FROM mf_score_run WHERE ruleset_version = ? ORDER BY run_id",
                                  (ruleset,))]
        out["sentences"] = int(q("SELECT count(*) FROM mf_sentence_score WHERE ruleset_version = ?",
                                 (ruleset,)).fetchone()[0])
        out["comments"] = int(q("SELECT count(*) FROM mf_comment_score WHERE ruleset_version = ?",
                                (ruleset,)).fetchone()[0])
        out["sentence_band"] = dict(tuple(r) for r in q(
            "SELECT band, count(*) FROM mf_sentence_score WHERE ruleset_version = ? GROUP BY band", (ruleset,)))
        out["sentence_gate_open"] = int(q("SELECT count(*) FROM mf_sentence_score WHERE ruleset_version = ?"
                                          " AND gate = 1", (ruleset,)).fetchone()[0])
        out["comment_band"] = dict(tuple(r) for r in q(
            "SELECT band, count(*) FROM mf_comment_score WHERE ruleset_version = ? GROUP BY band", (ruleset,)))
        out["comment_gate_open"] = int(q("SELECT count(*) FROM mf_comment_score WHERE ruleset_version = ?"
                                         " AND gate = 1", (ruleset,)).fetchone()[0])
        out["answerability"] = dict(tuple(r) for r in q(
            "SELECT level, count(*) FROM mf_comment_answerability WHERE ruleset_version = ? GROUP BY level",
            (ruleset,)))
        out["rules"] = [tuple(r) for r in q(
            "SELECT rule, count(*) FROM mf_sentence_hit WHERE ruleset_version = ?"
            " GROUP BY rule ORDER BY count(*) DESC", (ruleset,))]
        out["dimension_max"] = {}
        for col in DIM_COLS:
            out["dimension_max"][col] = dict(tuple(r) for r in q(
                f"SELECT {col}, count(*) FROM mf_comment_score WHERE ruleset_version = ? GROUP BY {col}",
                (ruleset,)))
        return out
