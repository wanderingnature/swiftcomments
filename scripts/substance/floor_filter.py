"""Substance-scoring PoC — Stage 1: the lexical floor filter.

Decides, for each analyzed comment, whether it can be auto-classified `minimal`
(gate=false) WITHOUT an LLM call. A comment floors iff it trips ZERO of four
cheap detectors, all evaluated against signals we already compute:

  1. named entity of a substantive type (GPE/LOC/ORG/DATE/QUANTITY/LAW/FAC/
     PERCENT/EVENT) in {analysis}.named_entities
  2. a citation / legal reference (regex over comment_text)
  3. deficiency language (regex over comment_text)
  4. a first-person empirical assertion (regex over comment_text)

Tuned for precision on "fail": if a comment trips ANY detector it survives to
the LLM.

Scope: the analyzed corpus = the originals of v_truly_unique_comments longer
than 100 characters, which is also the NER population. Writes {analysis}.substance_floor, one
row per comment, replacing the previous run's rows.

Prints what it is about to do and a progress line every 10,000 comments: the four
detectors run inside one query, the regexes as Python callbacks from SQLite, so the
query is the whole run.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_REPO_ROOT / ".env")
sys.path.insert(0, str(_REPO_ROOT))

from shared import db
from shared.project_context import dict_connect, ProjectContext, add_project_argument, context_from_args

SUBSTANTIVE_ENTITY_TYPES = (
    "GPE", "LOC", "ORG", "DATE", "QUANTITY", "LAW", "FAC", "PERCENT", "EVENT",
)

# Real document / legal citations — deliberately NOT bare "EA"/"BLM"/"EIS"
# (near-universal in this corpus). Section/table/figure/appendix/chapter must be
# followed by a number; statutes and CFR/USC citations count directly.
# Word boundaries are written \y (\b is a backspace here), \m start, \M end;
# shared/db.py's regexp() translates them.
CITATION_RE = (
    r"(section|sec\.|§|table|figure|fig\.|appendix|chapter)\s*\d"
    r"|\yp+\.?\s*\d"
    r"|\d+\s*(c\.?f\.?r\.?|u\.?s\.?c\.?)"
    r"|\y(c\.?f\.?r\.?|u\.?s\.?c\.?)\s*\d"
    r"|\yNEPA\y|National Environmental Policy Act"
    r"|\yESA\y|Endangered Species Act"
    r"|\yFLPMA\y|Federal Land Policy"
    r"|\yNHPA\y|National Historic Preservation Act"
    r"|Clean Water Act|Clean Air Act|Antiquities Act|Migratory Bird"
    r"|Executive Order\s*\d|\yAPD\y"
)

DEFICIENCY_RE = (
    r"fail(ed|s)? to|did not (consider|analyze|address|look|account|study|evaluate|examine)"
    r"|does(n'?t| not) (consider|address|account|analyze|evaluate|examine)"
    r"|not (adequately|sufficiently|properly) (consider|analyz|address|evaluat|studi)"
    r"|ignore[sd]?|overlook(ed|s|ing)?|inadequate|insufficient"
    r"|no analysis of|lack(s|ing)? (of )?analysis|missing (analysis|data)"
    r"|should have (considered|analyzed|studied|evaluated|examined)"
    r"|without (considering|analyzing|evaluating)|underestimat|fails to account"
)

# First-person subject near a perception/state/activity verb. Recall-tuned
# (a false positive costs one LLM call; a false negative loses a comment the
# agency should answer). See §4a fifth condition.
FIRSTPERSON_RE = (
    r"\y(i|we|my|our)\y[^.!?]{0,60}\y"
    r"(saw|seen|see|noticed?|watch(ed)?|observ(ed)?|witness(ed)?|"
    r"fish(ed)?|hunt(ed)?|hik(ed|e)?|walk(ed)?|camp(ed)?|rode|ride|drove|drive|"
    r"live[sd]?|lived|visit(ed)?|remember|grew up|breathe|drink|rely|depend)\y"
    r"|\y(saw|seen|noticed|watched|observed|witnessed|hunted|fished|hiked)\y"
    r"[^.!?]{0,30}\y(i|we|my|our)\y"
)

# The lexically analyzed comments (the originals of v_truly_unique_comments longer
# than 100 characters), and every comment scored on its own text: a
# shorter comment scored directly still needs its floor row — answerability reads
# has_citation for every scored comment and refuses a missing one.
BASE_SQL = """
    SELECT v.comment_id, v.comment_text
    FROM {analysis}.v_source_comments v
    WHERE EXISTS (SELECT 1 FROM {analysis}.v_truly_unique_comments u
                  WHERE u.comment_id = v.comment_id AND length(u.comment_text) > 100)
       OR EXISTS (SELECT 1 FROM {analysis}.substance_scores s
                  WHERE s.comment_id = v.comment_id AND s.scored_via <> 'inherited')
"""

COUNT_SQL = f"SELECT count(*) FROM ({BASE_SQL})"


def floor_sql(limit=None):
    """The floor query; with `limit`, over the first N of the population by
    comment id (a sample)."""
    base = BASE_SQL + ("    ORDER BY v.comment_id LIMIT :limit\n" if limit else "")
    return FLOOR_TEMPLATE.replace("BASE_SELECT", base)


FLOOR_TEMPLATE = """
WITH base AS (BASE_SELECT),
flags AS (
    SELECT
        b.comment_id,
        b.comment_text,
        EXISTS (
            SELECT 1 FROM {analysis}.named_entities e
            WHERE e.comment_id = b.comment_id
              AND e.entity_type IN (SELECT value FROM json_each(:ent_types))
        ) AS has_entity,
        b.comment_text REGEXP :citation AS has_citation,
        b.comment_text REGEXP :deficiency AS has_deficiency,
        b.comment_text REGEXP :firstperson AS has_firstperson
    FROM base b
)
SELECT
    comment_id,
    substr(comment_text, 1, 400) AS snippet,
    length(comment_text) AS len,
    has_entity, has_citation, has_deficiency, has_firstperson,
    NOT (has_entity OR has_citation OR has_deficiency OR has_firstperson) AS floored
FROM flags
"""


def run(ctx: ProjectContext, limit=None) -> None:
    params = {
        "ent_types": json.dumps(list(SUBSTANTIVE_ENTITY_TYPES)),
        "citation": "(?i)" + CITATION_RE,
        "deficiency": "(?i)" + DEFICIENCY_RE,
        "firstperson": "(?i)" + FIRSTPERSON_RE,
    }
    if limit:
        params["limit"] = limit
    with dict_connect(ctx.db_config) as conn:
        population = conn.execute(ctx.render_sql(COUNT_SQL)).fetchone()[0]
        total = min(limit, population) if limit else population
        print(f"=== Floor filter — {ctx.slug} ===")
        print(f"population: the originals of v_truly_unique_comments longer than 100 characters,"
              f" plus every comment scored on its own text: {population:,} comments")
        if limit:
            print(f"--limit {limit}: the first {total:,} of them by comment id; run without"
                  " --limit for all of them, or make jump STEP=floor for the stored rows")
        print("running four detectors per comment in one query (a named-entity lookup and three"
              " regexes, the regexes as Python callbacks from SQLite); progress every 10,000;"
              " then substance_floor is replaced, one row per comment", flush=True)
        rows = []
        t0 = time.monotonic()
        for row in conn.execute(ctx.render_sql(floor_sql(limit)), params):
            rows.append(row)
            n = len(rows)
            if n % 10000 == 0:
                elapsed = time.monotonic() - t0
                eta = elapsed / n * (total - n)
                print(f"  {n:,}/{total:,} comments in {elapsed:,.0f}s, about {eta:,.0f}s to go",
                      flush=True)
    assert len(rows) == total, f"the query returned {len(rows):,} rows for {total:,} comments"
    floored = [r for r in rows if r["floored"]]
    survived = [r for r in rows if not r["floored"]]
    n_floor = len(floored)

    def pct(n):
        return f"{100.0 * n / total:.1f}%" if total else "n/a"

    print(f"\nanalyzed comments (have features, or scored on their own text): {total:,}")
    print(f"floored (auto-minimal, no LLM):        {n_floor}  ({pct(n_floor)})")
    print(f"survive to LLM:                        {len(survived)}  ({pct(len(survived))})")
    print("\ndetector hit rates (survivors trip >=1):")
    for k in ("has_entity", "has_citation", "has_deficiency", "has_firstperson"):
        n = sum(1 for r in rows if r[k])
        print(f"  {k:16} {n:6}  ({pct(n)})")

    # Sole-reason breakdown: how often each detector is the ONLY thing keeping a
    # comment out of the floor (its marginal value).
    print("\nsole-survivor reason (only detector that fired):")
    for k in ("has_entity", "has_citation", "has_deficiency", "has_firstperson"):
        others = [o for o in ("has_entity", "has_citation", "has_deficiency", "has_firstperson") if o != k]
        n = sum(1 for r in rows if r[k] and not any(r[o] for o in others))
        print(f"  only {k:16} {n:6}  ({pct(n)})")

    # Floor decisions -> the DB (full recompute each run). The source of truth is the table;
    # no floor_decisions.csv.
    with db.connect(**ctx.db_config) as conn:
        before = conn.execute(ctx.render_sql(
            "SELECT count(*) FROM {analysis}.substance_floor")).fetchone()[0]
        print(f"\nwriting {len(rows):,} rows to substance_floor, replacing {before:,}", flush=True)
        with conn.cursor() as cur:
            cur.execute(ctx.render_sql("DELETE FROM {analysis}.substance_floor"))
            cur.executemany(ctx.render_sql(
                "INSERT INTO {analysis}.substance_floor (comment_id, floored, has_entity, "
                "has_citation, has_deficiency, has_firstperson, comment_len) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)"),
                [(r["comment_id"], r["floored"], r["has_entity"], r["has_citation"],
                  r["has_deficiency"], r["has_firstperson"], r["len"]) for r in rows])
        conn.commit()
    print(f"wrote {len(rows):,} floor decisions to substance_floor")


def main():
    parser = argparse.ArgumentParser(
        description="Substance-scoring floor filter: writes substance_floor.")
    add_project_argument(parser)
    parser.add_argument("--limit", type=int, metavar="N",
                        help="the first N comments of the population only (a sample);"
                             " the whole run later replaces them")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be >= 1")
    run(context_from_args(args), limit=args.limit)


if __name__ == "__main__":
    main()
