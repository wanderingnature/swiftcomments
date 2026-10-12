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
the LLM. See docs/plans/substance-scoring-poc.md (decision 3) and
docs/design/substance-scoring.md §4a.

Scope: the analyzed corpus = the originals of v_truly_unique_comments longer
than 100 characters (plan 5.2, edit 2: what the lexical pipeline's features
table held), which is also the NER population. Read-only; writes a CSV of decisions and a
markdown sample for eyeballing to the project's reports dir.
"""

import argparse
import json
import sys
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
# NB: Postgres regex word boundary is \y (\b is a backspace here), \m start, \M end.
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

FLOOR_SQL = f"""
WITH base AS (
    -- The lexically analyzed comments (the originals of v_truly_unique_comments
    -- longer than 100 characters, plan 5.2 edit 2), and every comment scored on its own
    -- text: a shorter comment scored directly still needs its floor row — answerability
    -- reads has_citation for every scored comment and refuses a missing one.
    SELECT v.comment_id, v.comment_text
    FROM {{analysis}}.v_source_comments v
    WHERE EXISTS (SELECT 1 FROM {{analysis}}.v_truly_unique_comments u
                  WHERE u.comment_id = v.comment_id AND length(u.comment_text) > 100)
       OR EXISTS (SELECT 1 FROM {{analysis}}.substance_scores s
                  WHERE s.comment_id = v.comment_id AND s.scored_via <> 'inherited')
),
flags AS (
    SELECT
        b.comment_id,
        b.comment_text,
        EXISTS (
            SELECT 1 FROM {{analysis}}.named_entities e
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


def run(ctx: ProjectContext) -> None:
    params = {
        "ent_types": json.dumps(list(SUBSTANTIVE_ENTITY_TYPES)),
        "citation": "(?i)" + CITATION_RE,
        "deficiency": "(?i)" + DEFICIENCY_RE,
        "firstperson": "(?i)" + FIRSTPERSON_RE,
    }
    with dict_connect(ctx.db_config) as conn:
        rows = conn.execute(ctx.render_sql(FLOOR_SQL), params).fetchall()

    total = len(rows)
    floored = [r for r in rows if r["floored"]]
    survived = [r for r in rows if not r["floored"]]
    n_floor = len(floored)

    def pct(n):
        return f"{100.0 * n / total:.1f}%" if total else "n/a"

    print(f"\n=== Floor filter — {ctx.slug} ===")
    print(f"analyzed comments (have features, or scored on their own text): {total}")
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
        with conn.cursor() as cur:
            cur.execute(ctx.render_sql("DELETE FROM {analysis}.substance_floor"))
            cur.executemany(ctx.render_sql(
                "INSERT INTO {analysis}.substance_floor (comment_id, floored, has_entity, "
                "has_citation, has_deficiency, has_firstperson, comment_len) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)"),
                [(r["comment_id"], r["floored"], r["has_entity"], r["has_citation"],
                  r["has_deficiency"], r["has_firstperson"], r["len"]) for r in rows])
        conn.commit()
    print(f"\nwrote {len(rows)} floor decisions to substance_floor")


def main():
    parser = argparse.ArgumentParser(description="Substance-scoring floor filter (read-only).")
    add_project_argument(parser)
    args = parser.parse_args()
    run(context_from_args(args))


if __name__ == "__main__":
    main()
