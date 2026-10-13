#!/usr/bin/env python3
"""The mechanical substantive screen — three classes, marked per comment.

The design doc's divide (substance-scoring.md §2): presence is countable,
linkage needs comprehension. This is the presence half as a FINAL screen,
built on the layers the pipeline already owns — the entity-tagging pipeline's
confirmed citations (`comment_authorities`, `comment_cited_references`), the
spaCy NER record (`named_entities`), and citation/deficiency/referent grammar
— zero model calls.

Classes (engage only the highest bar):

  A   anchored — a confirmed legal-authority citation, a confirmed third-
      party reference, a citation into a document, or deficiency language
      aimed at a named referent of THIS action. The agency-response layers
      engage class A only.
  B1  specific but unanchored — names this action's referents and carries
      analytical content (deficiency language, or NER-measured evidence
      density) without an anchor.
  B2  pure stance — engages nothing of this action mechanically.

CAMPAIGN SUPPRESSION: signals count
only from text the submitter contributed, not from mass-duplicated campaign
boilerplate — otherwise one citation-shaped sentence in a form letter marks
every signer 'A'. The shared/own split is the stored family attribution
(shared_text.load_shapes; families.py decides it, build_comment_groups.py
--write stores it, so the partition precedes this step), and NO signal
fires from shared text:
the regex signals see own text only, confirmed authority/reference tags are
dropped when their matched_text sits inside a boilerplate span, and NER
evidence entities inside those spans do not count. The campaign's content
still counts ONCE — on its cluster exemplar, which is what the scoring queue
sends.

POPULATION: the floor-filter survivors, NOT the already-scored set. The
screen now runs BEFORE scoring — it decides what is worth paying for
— so it cannot depend on what has
already been scored.

    python scripts/substance/mechanical_screens.py --project roadless
    python scripts/substance/mechanical_screens.py --project roadless --write

Prints each stage as it starts and a line every 20,000 comments screened.

Without --write: read-only evaluation (class distribution, crosstabs against
the LLM dimensions, spot checks). With --write: replaces the full marking in
{analysis}.substance_screen (its class/signal derivation CHECK is identical to
classify()).
"""

import argparse
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_HERE.parent))   # scripts/substance

from shared import db  # noqa: E402
from shared.instrument import SCORING_INSTRUMENT  # noqa: E402
from shared.project_context import add_project_argument, context_from_args  # noqa: E402

import shared_text  # noqa: E402

# The reference token after the keyword must be a digit, a roman numeral, or
# a single capital — (?-i:...) keeps that case-sensitive under IGNORECASE
# ("water table beneath" is not a table citation).
# The two alternatives are named because the v3 grader (grade.py) separates
# them: a numbered reference is DOC 3, a characterization is DOC 2. _DOC_CITE
# is their union and is unchanged.
DOC_NUMBERED = (r"\b(?:section|sec\.|§|page|p\.|pp\.|figure|fig\.|table|chapter|"
                r"appendix|volume|vol\.)\s*(?:\d|(?-i:[IVX]+\b|[A-Z]\b))")
DOC_CHARACTERIZED = (r"\b(?:DEIS|EIS|draft environmental impact statement)\s+(?:at|states|"
                     r"acknowledges|concedes|admits|claims|asserts|says)\b")
DOC_NUMBERED_RE = re.compile(DOC_NUMBERED, re.IGNORECASE)
DOC_CHARACTERIZED_RE = re.compile(DOC_CHARACTERIZED, re.IGNORECASE)
_DOC_CITE = re.compile(f"({DOC_NUMBERED}|{DOC_CHARACTERIZED})", re.IGNORECASE)

_ACTION_REF = re.compile(
    r"(FS-2025-0001|RIN\s*0596"
    r"|\bDEIS\b|\bEIS\b|environmental impact statement"
    r"|\brescission\b|\brescind\w*"
    r"|\balternative\s*(?:1|2|3|one|two|three)\b|no.action alternative"
    r"|\bpurpose and need\b|\bproposed rule\b|\bthis rulemaking\b"
    r"|\bthe proposal\b|\bdocket\b)",
    re.IGNORECASE)

_DEFICIENCY = re.compile(
    r"(\bfail(?:s|ed|ure)?\s+to\b"
    r"|\bdoes\s+not\s+(?:analyze|consider|address|disclose|account|quantify|"
    r"evaluate|examine|assess|support|justify|explain)\b"
    r"|\bdid\s+not\s+(?:analyze|consider|address|disclose|account|quantify|"
    r"evaluate|examine|assess)\b"
    r"|\bignor(?:es|ed|ing)\b|\binadequate\w*\b|\binsufficient\w*\b"
    r"|\bunder(?:state|estimate)\w*\b|\boverstate\w*\b"
    r"|\bno\s+analysis\b|\bnot\s+analyzed\b|\bunsupported\b"
    r"|\bomit(?:s|ted)\b|\blacks\b|\bmissing\s+(?:analysis|data)\b"
    r"|\bcontradict\w*\b|\barbitrary\s+and\s+capricious\b"
    r"|\bmischaracteriz\w*\b|\bunexamined\b)",
    re.IGNORECASE)

_EVID_TYPES = ("PERCENT", "MONEY", "QUANTITY", "LAW")


def classify(authority, reference, doc_cite, action_ref, deficiency,
             evid_ner):
    if authority or reference or doc_cite or (deficiency and action_ref):
        return "A"
    if action_ref and (deficiency or evid_ner):
        return "B1"
    return "B2"


def compute(ctx, shapes=None, limit=None):
    """(comment_id -> signal dict + class) for every floor-filter survivor.
    All inputs are existing DB layers; no model calls. `shapes` (from
    shared_text.load_shapes) is accepted so a caller that already loaded the
    shared/own split — the scoring queue — does not read it twice. The split
    is the stored family attribution, so the partition (build_comment_groups
    --write) precedes this step. `limit` screens the first N survivors only
    (a sample)."""
    with db.connect(**ctx.db_config) as conn:
        print("loading the floor survivors and their shared/own text split", flush=True)
        rows = shared_text.load_corpus(conn, ctx.render_sql)
        if shapes is None:
            shapes = shared_text.load_shapes(conn, ctx.render_sql)
        if limit:
            print(f"  --limit {limit}: the first {min(limit, len(rows)):,} of {len(rows):,} survivors;"
                  " run without --limit for all of them, or make jump STEP=screen for the"
                  " stored rows", flush=True)
            rows = rows[:limit]
        print(f"  {len(rows):,} survivors; loading the confirmed citations and the NER"
              " evidence entities", flush=True)
        tags = {}
        for table, key in (("comment_authorities", "authority"),
                           ("comment_cited_references", "reference")):
            for cid, mt in conn.execute(ctx.render_sql(
                    "SELECT comment_id, matched_text"
                    f" FROM {{analysis}}.{table}")):
                tags.setdefault(cid, {}).setdefault(key, []).append(mt or "")
        ents = {}
        for cid, cs in conn.execute(ctx.render_sql(
                "SELECT comment_id, char_start"
                " FROM {analysis}.named_entities"
                " WHERE entity_type IN (SELECT value FROM json_each(?))"), (json.dumps(list(_EVID_TYPES)),)):
            ents.setdefault(cid, []).append(cs)

    print(f"screening {len(rows):,} comments (six signals over own text, then the class);"
          " a line every 20,000", flush=True)
    out = {}
    for n, (cid, _text) in enumerate(rows, 1):
        if n % 20000 == 0:
            print(f"  {n:,}/{len(rows):,}", flush=True)
        sh = shapes[cid]
        own_text = sh.own_text

        def tag_ok(matched_list, sh=sh):
            # A confirmed tag counts unless its matched text sits inside a
            # boilerplate span of THIS comment.
            for mt in matched_list:
                if not mt:
                    continue
                i = sh.text.find(mt)
                if i < 0:
                    return True  # not locatable — keep the pipeline's word
                if not sh.in_boilerplate(i):
                    return True
            return False

        ctags = tags.get(cid, {})
        n_evid = sum(1 for cs in ents.get(cid, [])
                     if cs is not None and not sh.in_boilerplate(cs))
        sig = {"authority": bool(ctags.get("authority"))
               and tag_ok(ctags.get("authority", [])),
               "reference": bool(ctags.get("reference"))
               and tag_ok(ctags.get("reference", [])),
               "doc_cite": bool(_DOC_CITE.search(own_text)),
               "action_ref": bool(_ACTION_REF.search(own_text)),
               "deficiency": bool(_DEFICIENCY.search(own_text)),
               "evid_ner": n_evid >= 2}
        sig_out: dict[str, object] = dict(sig)
        sig_out["screen_class"] = classify(**sig)
        out[cid] = sig_out
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    add_project_argument(p)
    p.add_argument("--write", action="store_true",
                   help="replace the marking in {analysis}.substance_screen"
                        " (default: read-only evaluation)")
    p.add_argument("--limit", type=int, metavar="N",
                   help="screen the first N survivors only (a sample); the whole run"
                        " later replaces them")
    args = p.parse_args()
    if args.limit is not None and args.limit < 1:
        p.error("--limit must be >= 1")
    ctx = context_from_args(args)

    marks = compute(ctx, limit=args.limit)
    n = len(marks)
    dist = {}
    for s in marks.values():
        dist[s["screen_class"]] = dist.get(s["screen_class"], 0) + 1
    print(f"screened {n} comments: "
          + " | ".join(f"{c}: {dist.get(c, 0)}" for c in ("A", "B1", "B2")),
          flush=True)

    if args.write:
        print(f"writing {n:,} rows to substance_screen, replacing the previous marking",
              flush=True)
        rows = [(cid, s["screen_class"], s["authority"], s["reference"],
                 s["doc_cite"], s["action_ref"], s["deficiency"],
                 s["evid_ner"]) for cid, s in marks.items()]
        with db.connect(**ctx.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(ctx.render_sql(
                    "DELETE FROM {analysis}.substance_screen"))
                cur.executemany(ctx.render_sql(
                    "INSERT INTO {analysis}.substance_screen"
                    " (comment_id, screen_class, authority, reference,"
                    "  doc_cite, action_ref, deficiency, evid_ner)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"), rows)
            conn.commit()
        print(f"marking written: {len(rows)} rows replace"
              " substance_screen", flush=True)
        return

    # Read-only evaluation: crosstab against the gate + spot checks.
    with db.connect(**ctx.db_config) as conn:
        gates = dict(conn.execute(ctx.render_sql(
            "SELECT comment_id, gate FROM {analysis}.substance_scores"
            " WHERE NOT was_floored AND instrument_version = ?"),
            (SCORING_INSTRUMENT,)))
    gate_by_class = {}
    for cid, s in marks.items():
        k = (s["screen_class"], gates.get(cid, False))
        gate_by_class[k] = gate_by_class.get(k, 0) + 1
    for c in ("A", "B1", "B2"):
        print(f"  class {c}: gate-true {gate_by_class.get((c, True), 0)},"
              f" gate-false {gate_by_class.get((c, False), 0)}")
    for ex in ("FS-2025-0001-253498",      # an opinion exemplar
               "FS-2025-0001-308181",      # a campaign signer
               "FS-2025-0001-309831"):
        if ex in marks:
            print(f"spot check {ex}: {marks[ex]}")


if __name__ == "__main__":
    main()
