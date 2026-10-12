#!/usr/bin/env python3
"""Load consolidated classifications into the analysis schema — directly, in code.

Replaces the generate-a-.sh-and-shell-psql load stage. The old path had
generate_batch_sql.py emit numbered .sql files plus an execute_batches_<TS>.sh
wrapper, then the pipeline ran `bash …` → `psql -f …`. A data problem surfaced as
a raw psql crash the app couldn't see or handle — e.g. a comment that carries the
same topic twice produced two rows with the same (classification_id, topic_id) in
one `INSERT … ON CONFLICT`, and Postgres refuses to affect a row twice in one
command ("ON CONFLICT DO UPDATE command cannot affect row a second time").

This does the load in code, with the libraries already in hand:
- **De-duplicates** in Python before the write — one classification per comment,
  one topic row per (comment, topic) keeping the highest confidence — so no
  INSERT ever proposes a conflict key twice. That is the fix for the crash.
- Runs the whole load in **one transaction** (deactivate old → insert
  classifications → insert topics); any failure rolls the whole thing back.
- Surfaces real errors (bad sentiment, unknown topic, DB failure) as Python
  exceptions with context — no silent psql exit code. An unknown topic name fails
  the load with every such name; it is never skipped.

Input is the same consolidated CSV parse_multi_batch_results.py writes; the target
schema, sentiment map, and model name come from the batch_metadata_<TS>.json
snapshot (reused via generate_batch_sql.load_snapshot) — never guessed.

    python scripts/load_classifications.py --project <slug> \
        analysis_results/<slug>/consolidated_classifications_<TS>.csv

Reads and writes data/roadless.sqlite through shared/db.py.
"""

import argparse
from datetime import datetime
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from shared import db  # noqa: E402
from shared.instrument import model_of  # noqa: E402
from shared.project_context import ProjectContext  # noqa: E402
from generate_batch_sql import load_snapshot  # noqa: E402  (one snapshot loader, reused)

_VALID_STRENGTH = ("HIGH", "MEDIUM", "LOW")
_MIN_TOPIC_CONFIDENCE = 0.7  # matches the prior SQL generator's topic threshold

# The topic a comment gets when it states a position and nothing more. The prompt
# asks for it with no supporting phrases — output tokens spent on a fixed string —
# and chk_phrase_count requires one, so the loader supplies it.
SENTIMENT_ONLY = "sentiment_only"
SENTIMENT_ONLY_PHRASE = "This comment is sentiment only"


def _one(cur):
    """The single row a count query must return. No row means the query is wrong."""
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("expected one row, got none")
    return row


def _batch_id_from_csv(csv_path: str) -> str:
    """The batch id is the generation timestamp carried in the CSV filename —
    the same value that links comment_classification rows and the snapshot."""
    m = re.search(r"consolidated_classifications_(\d{8}_\d{6})", Path(csv_path).stem)
    if not m:
        raise ValueError(
            f"Cannot derive batch timestamp from {csv_path!r} — expected"
            " consolidated_classifications_<TS>.csv")
    return m.group(1)


def _aggregate(rows, sentiment_map):
    """Collapse the per-topic CSV rows into per-comment classifications and a
    de-duplicated topic set. Raises on missing/invalid sentiment (NO FALLBACKS)."""
    comments = {}                      # comment_id -> classification dict
    conf_sum = defaultdict(float)      # comment_id -> summed topic confidence
    conf_n = defaultdict(int)
    topics = defaultdict(dict)         # comment_id -> {topic_name: (confidence, phrases)}
    skipped_no_phrases = 0

    for row in rows:
        comment_id = (row.get("comment_id") or "").strip()
        if not comment_id:
            continue

        if comment_id not in comments:
            stance = (row.get("sentiment") or "").strip().upper()
            strength = (row.get("sentiment_strength") or "").strip().upper()
            if not stance:
                raise ValueError(f"Missing sentiment for comment {comment_id}")
            if not strength:
                raise ValueError(f"Missing sentiment_strength for comment {comment_id}")
            if stance not in sentiment_map:
                raise ValueError(
                    f"Invalid sentiment {stance!r} for comment {comment_id}."
                    f" Valid: {sorted(sentiment_map)}")
            if strength not in _VALID_STRENGTH:
                raise ValueError(
                    f"Invalid sentiment_strength {strength!r} for comment {comment_id}."
                    f" Valid: {list(_VALID_STRENGTH)}")
            comments[comment_id] = {
                "comment_id": comment_id,
                "sentiment_id": sentiment_map[stance],
                "sentiment_strength": strength,
                "custom_id": (row.get("custom_id") or comment_id),
            }

        topic_name = (row.get("topic_name") or "").strip()
        try:
            confidence = float(row.get("topic_confidence") or 0.0)
        except ValueError:
            confidence = 0.0
        if confidence:
            conf_sum[comment_id] += confidence
            conf_n[comment_id] += 1

        if not topic_name or confidence < _MIN_TOPIC_CONFIDENCE:
            continue
        raw = row.get("supporting_phrases") or ""
        # A list from classification_rows (the re-classify runner) keeps a phrase
        # containing '|' whole; the CSV carries them '|'-joined.
        parts = raw if isinstance(raw, list) else raw.split("|")
        phrases = [str(p).strip() for p in parts if str(p).strip()]
        if not phrases and topic_name == SENTIMENT_ONLY:
            phrases = [SENTIMENT_ONLY_PHRASE]
        if not phrases:
            # chk_phrase_count forbids a phrase-less topic row; the model declined
            # to ground it. Skip the topic (the comment + grounded topics still load).
            skipped_no_phrases += 1
            continue
        # De-dup on (comment, topic): keep the highest-confidence occurrence, so a
        # comment that names a topic twice never produces a duplicate conflict key.
        existing = topics[comment_id].get(topic_name)
        if existing is None or confidence > existing[0]:
            topics[comment_id][topic_name] = (confidence, phrases)

    for c in comments.values():
        cid = c["comment_id"]
        c["confidence_score"] = round(conf_sum[cid] / conf_n[cid], 2) if conf_n[cid] else 0.0
    return comments, topics, skipped_no_phrases


# Every group member paired with the group's source: the canonical comment when it
# has an active classification, else the lowest-id member classified by its own
# model call. comment_group holds every comment in exactly one group (exact,
# middle-content, family, campaign or singleton), so this one layer covers all.
_PAIRS = (
    "WITH gs AS ("
    "  SELECT g.group_id, coalesce("
    "    (SELECT g.canonical_comment_id WHERE EXISTS ("
    "       SELECT 1 FROM {analysis}.comment_classification c0"
    "       WHERE c0.comment_id = g.canonical_comment_id AND c0.is_active)),"
    "    (SELECT min(m.comment_id) FROM {analysis}.comment_group_member m"
    "     JOIN {analysis}.comment_classification c1"
    "       ON c1.comment_id = m.comment_id AND c1.is_active"
    "      AND c1.created_by <> 'dedup_propagate'"
    "     WHERE m.group_id = g.group_id)) AS src_id"
    "  FROM {analysis}.comment_group g)"
    " SELECT m.comment_id AS dup_id, gs.src_id"
    " FROM {analysis}.comment_group_member m JOIN gs ON gs.group_id = m.group_id"
    " WHERE gs.src_id IS NOT NULL AND m.comment_id <> gs.src_id")


def _propagate_to_duplicates(conn, ctx, batch_id, original_ids):
    """Copy each group's classification onto every member of its comment group.

    We classify one comment per group (exact, middle-content, family, campaign or
    singleton) and mirror the result onto the members: a copied template carries
    the template's stance whatever the commenter wrote around it, so every comment
    carries a row without a per-member LLM call. Idempotent:

    - Deactivates PROPAGATED rows (created_by 'dedup_propagate') of the members of
      every group containing a comment in `original_ids`, so a re-load refreshes the
      group. A row a member got from its own model call is never touched.
    - Then fills EVERY member that lacks an active classification from its group's
      source (a GLOBAL fill, so a new member of a previously-classified group is
      also covered, not just this batch's).

    Returns the number of comments given a classification.
    """
    stale = ctx.render_sql(
        "SELECT cc.classification_id FROM {analysis}.comment_classification cc"
        " JOIN {analysis}.comment_group_member m ON m.comment_id = cc.comment_id"
        " WHERE cc.is_active AND cc.created_by = 'dedup_propagate'"
        "   AND m.group_id IN (SELECT m2.group_id FROM {analysis}.comment_group_member m2"
        "                      WHERE m2.comment_id IN (SELECT value FROM json_each(:ids)))")
    conn.execute(ctx.render_sql(
        "UPDATE {analysis}.classification_topics SET is_active = false,"
        " updated_date = CURRENT_TIMESTAMP, updated_by = 'dedup_propagate'"
        " WHERE classification_id IN (") + stale + ")", {"ids": json.dumps(original_ids)})
    conn.execute(ctx.render_sql(
        "UPDATE {analysis}.comment_classification SET is_active = false,"
        " updated_date = CURRENT_TIMESTAMP, updated_by = 'dedup_propagate'"
        " WHERE classification_id IN (") + stale + ")", {"ids": json.dumps(original_ids)})

    n = 0
    for pairs in (ctx.render_sql(_PAIRS),):
        cur = conn.execute(ctx.render_sql(
            "WITH p AS (") + pairs + ctx.render_sql("), src AS ("
            "  SELECT p.dup_id, occ.sentiment_id, occ.sentiment_strength,"
            "         occ.confidence_score, occ.model_version"
            "  FROM p JOIN {analysis}.comment_classification occ"
            "    ON occ.comment_id = p.src_id AND occ.is_active"
            "  WHERE NOT EXISTS (SELECT 1 FROM {analysis}.comment_classification x"
            "                    WHERE x.comment_id = p.dup_id AND x.is_active)"
            ")"
            " INSERT INTO {analysis}.comment_classification"
            "   (comment_id, sentiment_id, sentiment_strength, batch_id, model_version,"
            "    custom_id, confidence_score, created_by, processed_date, is_active)"
            " SELECT dup_id, sentiment_id, sentiment_strength, ?, model_version,"
            "        'propagated', confidence_score, 'dedup_propagate', CURRENT_TIMESTAMP, true FROM src"
            " WHERE true"
            " ON CONFLICT (comment_id, batch_id) DO UPDATE SET"
            "   sentiment_id = EXCLUDED.sentiment_id, sentiment_strength = EXCLUDED.sentiment_strength,"
            "   confidence_score = EXCLUDED.confidence_score, model_version = EXCLUDED.model_version,"
            "   is_active = true, updated_date = CURRENT_TIMESTAMP, updated_by = 'dedup_propagate'"),
            (batch_id,))
        n += cur.rowcount
        # Topic rows for the just-propagated copies, copied from their source.
        conn.execute(ctx.render_sql(
            "WITH p AS (") + pairs + ctx.render_sql(")"
            " INSERT INTO {analysis}.classification_topics"
            "  (classification_id, topic_id, confidence, supporting_phrases, rank_order,"
            "   created_by, is_active)"
            " SELECT dcc.classification_id, ct.topic_id, ct.confidence, ct.supporting_phrases,"
            "        ct.rank_order, 'dedup_propagate', true"
            " FROM p"
            " JOIN {analysis}.comment_classification dcc"
            "   ON dcc.comment_id = p.dup_id AND dcc.is_active"
            " JOIN {analysis}.comment_classification occ"
            "   ON occ.comment_id = p.src_id AND occ.is_active"
            " JOIN {analysis}.classification_topics ct"
            "   ON ct.classification_id = occ.classification_id AND ct.is_active"
            " WHERE dcc.created_by = 'dedup_propagate'"
            "   AND NOT EXISTS (SELECT 1 FROM {analysis}.classification_topics y"
            "                   WHERE y.classification_id = dcc.classification_id AND y.is_active)"
            " ON CONFLICT (classification_id, topic_id) DO UPDATE SET"
            "   confidence = EXCLUDED.confidence, supporting_phrases = EXCLUDED.supporting_phrases,"
            "   rank_order = EXCLUDED.rank_order, is_active = true, updated_date = CURRENT_TIMESTAMP,"
            "   updated_by = 'dedup_propagate'"))
    return n


def _insert_classifications(conn, ctx, comments, topics, batch_id, model_name):
    """Insert one classification per comment and its de-duplicated, ranked topic
    rows (created_by 'batch_processor'), inside the caller's transaction. The
    caller has already deactivated the comments' previous rows.

    A topic name not in {analysis}.topics raises with every such name: the row
    would otherwise be dropped, and a taxonomy the prompt and the table disagree
    on is a setup error, not a per-comment one. Returns ({comment_id:
    classification_id}, topic rows inserted).
    """
    topic_id_by_name = dict(conn.execute(ctx.render_sql(
        "SELECT topic_name, topic_id FROM {analysis}.topics")).fetchall())
    unknown = sorted({t for tmap in topics.values() for t in tmap} - set(topic_id_by_name))
    if unknown:
        raise ValueError(
            f"Topic name(s) not in topics: {unknown} —"
            " nothing loaded.")

    class_id = {}
    ins_class = ctx.render_sql(
        "INSERT INTO {analysis}.comment_classification"
        " (comment_id, sentiment_id, sentiment_strength, batch_id, model_version,"
        "  custom_id, confidence_score, created_by, processed_date, is_active)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, 'batch_processor', CURRENT_TIMESTAMP, true)"
        " ON CONFLICT (comment_id, batch_id) DO UPDATE SET"
        "  sentiment_id = EXCLUDED.sentiment_id,"
        "  sentiment_strength = EXCLUDED.sentiment_strength,"
        "  confidence_score = EXCLUDED.confidence_score,"
        "  model_version = EXCLUDED.model_version,"
        "  is_active = true, updated_date = CURRENT_TIMESTAMP, updated_by = 'batch_processor'"
        " RETURNING classification_id")
    for cid, c in comments.items():
        cur = conn.execute(ins_class, (
            c["comment_id"], c["sentiment_id"], c["sentiment_strength"], batch_id,
            model_name, c["custom_id"], c["confidence_score"]))
        class_id[cid] = _one(cur)[0]

    topic_rows = []
    for cid, tmap in topics.items():
        ranked = sorted(tmap.items(), key=lambda kv: kv[1][0], reverse=True)
        for rank, (tname, (confidence, phrases)) in enumerate(ranked, 1):
            topic_rows.append((class_id[cid], topic_id_by_name[tname], confidence,
                               json.dumps(phrases), rank))

    # One executemany; keys are unique by construction, so ON CONFLICT can only
    # fire across runs (re-load), never within this statement.
    if topic_rows:
        conn.cursor().executemany(ctx.render_sql(
            "INSERT INTO {analysis}.classification_topics"
            " (classification_id, topic_id, confidence, supporting_phrases,"
            "  rank_order, created_by, is_active)"
            " VALUES (?, ?, ?, ?, ?, 'batch_processor', true)"
            " ON CONFLICT (classification_id, topic_id) DO UPDATE SET"
            "  confidence = EXCLUDED.confidence,"
            "  supporting_phrases = EXCLUDED.supporting_phrases,"
            "  rank_order = EXCLUDED.rank_order,"
            "  is_active = true, updated_date = CURRENT_TIMESTAMP, updated_by = 'batch_processor'"),
            topic_rows)
    return class_id, len(topic_rows)


def replace_groups(conn, ctx, group_ids, comments, topics, batch_id, model_name):
    """Make each group's new classification the one every member carries —
    the re-classify load (reclassify_groups.py), inside the caller's transaction.

    `comments`/`topics` are _aggregate() output for the groups' canonicals. For
    the groups in `group_ids` only:
    1. deactivate every member's active rows, canonical included, whether the
       member got them from its own model call or by propagation (a letter is
       one group: the group's answer stands for all of it);
    2. insert the canonicals' rows and topics (_insert_classifications);
    3. copy them onto every other member (created_by 'dedup_propagate',
       batch_id = the run's).
    Rows are deactivated, never deleted. Returns (classification ids by
    canonical, topic rows inserted, member rows written).
    """
    member_ids = ctx.render_sql(
        "SELECT comment_id FROM {analysis}.comment_group_member"
        " WHERE group_id IN (SELECT value FROM json_each(:g))")
    conn.execute(ctx.render_sql(
        "UPDATE {analysis}.classification_topics SET is_active = false,"
        " updated_date = CURRENT_TIMESTAMP, updated_by = 'reclassify'"
        " WHERE is_active AND classification_id IN ("
        "   SELECT classification_id FROM {analysis}.comment_classification"
        "   WHERE is_active AND comment_id IN (") + member_ids + "))",
        {"g": json.dumps(group_ids)})
    conn.execute(ctx.render_sql(
        "UPDATE {analysis}.comment_classification SET is_active = false,"
        " updated_date = CURRENT_TIMESTAMP, updated_by = 'reclassify'"
        " WHERE is_active AND comment_id IN (") + member_ids + ")",
        {"g": json.dumps(group_ids)})

    class_id, n_topic_rows = _insert_classifications(
        conn, ctx, comments, topics, batch_id, model_name)

    # Every non-canonical member of a group whose canonical was just loaded.
    pairs = ctx.render_sql(
        " FROM {analysis}.comment_group g"
        " JOIN {analysis}.comment_group_member m"
        "   ON m.group_id = g.group_id AND m.comment_id <> g.canonical_comment_id"
        " JOIN {analysis}.comment_classification c"
        "   ON c.comment_id = g.canonical_comment_id AND c.batch_id = :b")
    in_groups = " WHERE g.group_id IN (SELECT value FROM json_each(:g))"
    cur = conn.execute(ctx.render_sql(
        "INSERT INTO {analysis}.comment_classification"
        " (comment_id, sentiment_id, sentiment_strength, batch_id, model_version,"
        "  custom_id, confidence_score, created_by, processed_date, is_active)"
        " SELECT m.comment_id, c.sentiment_id, c.sentiment_strength, c.batch_id,"
        "        c.model_version, 'propagated', c.confidence_score, 'dedup_propagate',"
        "        CURRENT_TIMESTAMP, true") + pairs + in_groups + ctx.render_sql(
        " ON CONFLICT (comment_id, batch_id) DO UPDATE SET"
        "  sentiment_id = EXCLUDED.sentiment_id,"
        "  sentiment_strength = EXCLUDED.sentiment_strength,"
        "  confidence_score = EXCLUDED.confidence_score,"
        "  model_version = EXCLUDED.model_version,"
        "  is_active = true, updated_date = CURRENT_TIMESTAMP, updated_by = 'dedup_propagate'"),
        {"b": batch_id, "g": json.dumps(group_ids)})
    n_members = cur.rowcount
    conn.execute(ctx.render_sql(
        "INSERT INTO {analysis}.classification_topics"
        " (classification_id, topic_id, confidence, supporting_phrases, rank_order,"
        "  created_by, is_active)"
        " SELECT d.classification_id, ct.topic_id, ct.confidence, ct.supporting_phrases,"
        "        ct.rank_order, 'dedup_propagate', true") + pairs + ctx.render_sql(
        " JOIN {analysis}.comment_classification d"
        "   ON d.comment_id = m.comment_id AND d.batch_id = :b"
        " JOIN {analysis}.classification_topics ct"
        "   ON ct.classification_id = c.classification_id AND ct.is_active") + in_groups + (
        " ON CONFLICT (classification_id, topic_id) DO UPDATE SET"
        "  confidence = EXCLUDED.confidence, supporting_phrases = EXCLUDED.supporting_phrases,"
        "  rank_order = EXCLUDED.rank_order, is_active = true, updated_date = CURRENT_TIMESTAMP,"
        "  updated_by = 'dedup_propagate'"),
        {"b": batch_id, "g": json.dumps(group_ids)})
    return class_id, n_topic_rows, n_members


def load_classifications(ctx: ProjectContext, snapshot: dict, csv_path: str,
                         model_used: str | None = None) -> dict:
    """Load one consolidated CSV into {analysis}.comment_classification +
    classification_topics in a single transaction. Returns a summary dict.

    model_used is the model the RUN actually used (passed by the runner). It may
    differ from the profile's model_name captured in the snapshot at generation time
    — e.g. a local run through the LiteLLM proxy vs the profile's paid Together model.
    When given it is what gets recorded, so comment_classification.model_version and
    the classification_runs row reflect reality; falls back to the snapshot model."""
    if snapshot["analysis_schema"] != ctx.analysis_schema:
        raise ValueError(
            f"Snapshot analysis_schema {snapshot['analysis_schema']!r} != project"
            f" schema {ctx.analysis_schema!r} — wrong project or snapshot.")
    sentiment_map = {k: int(v) for k, v in snapshot["sentiment_map"].items()}
    # Stamped with the model behind the run's endpoint, never the endpoint.
    model_name = model_of(model_used) if model_used else snapshot["model_name"]
    batch_id = _batch_id_from_csv(csv_path)

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    comments, topics, skipped_no_phrases = _aggregate(rows, sentiment_map)
    if not comments:
        raise ValueError(f"No classifications in {csv_path} — nothing to load.")

    comment_ids = list(comments)

    with db.connect(**ctx.db_config) as conn:
        with conn.transaction():
            # 1. Deactivate the currently-active rows for these comments (topics
            #    first, selected via the still-active classifications).
            conn.execute(ctx.render_sql(
                "UPDATE {analysis}.classification_topics SET is_active = false,"
                " updated_date = CURRENT_TIMESTAMP, updated_by = 'batch_processor'"
                " WHERE classification_id IN ("
                "   SELECT classification_id FROM {analysis}.comment_classification"
                "   WHERE comment_id IN (SELECT value FROM json_each(?)) AND is_active = true)"),
                (json.dumps(comment_ids),))
            conn.execute(ctx.render_sql(
                "UPDATE {analysis}.comment_classification SET is_active = false,"
                " updated_date = CURRENT_TIMESTAMP, updated_by = 'batch_processor'"
                " WHERE comment_id IN (SELECT value FROM json_each(?)) AND is_active = true"),
                (json.dumps(comment_ids),))

            # 2-4. One classification per comment, then its ranked topic rows.
            _, n_topic_rows = _insert_classifications(
                conn, ctx, comments, topics, batch_id, model_name)

            # 5. Propagate each classified comment onto the members of its comment
            #    group — no per-member LLM call.
            n_propagated = _propagate_to_duplicates(conn, ctx, batch_id, comment_ids)

            # 6. Correct classification_runs.model_name to the model actually used.
            #    The row was inserted at generation time with the profile's model,
            #    before local/cloud was chosen; run_timestamp is the generation
            #    datetime (sub-second), whose truncation to the second equals the
            #    batch_id timestamp string.
            if model_used:
                conn.execute(ctx.render_sql(
                    "UPDATE {analysis}.classification_runs SET model_name = ?"
                    " WHERE strftime('%Y%m%d_%H%M%S', run_timestamp) = ?"),
                    (model_name, batch_id))

    return {
        "batch_id": batch_id, "comments": len(comments), "topic_rows": n_topic_rows,
        "propagated_duplicates": n_propagated,
        "skipped_no_phrases": skipped_no_phrases,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument("--project", required=True, help="Project slug")
    p.add_argument("csv_path", nargs="?",
                   help="consolidated_classifications_<TS>.csv from the parse stage")
    p.add_argument("--propagate-only", action="store_true",
                   help="Load nothing; copy existing classifications onto every comment-group"
                        " member that has none. For an hour whose new comments all joined"
                        " groups that are already classified.")
    p.add_argument("--metadata", help="Explicit batch_metadata_<TS>.json snapshot path")
    p.add_argument("--model-used", help="Model the run actually used (e.g. qwen-coder for a"
                   " local proxy run). Recorded instead of the snapshot's model_name so the"
                   " Classification Runs table and comment_classification reflect reality.")
    args = p.parse_args()

    ctx = ProjectContext.load(args.project)
    if args.propagate_only:
        batch_id = "propagate_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        with db.connect(**ctx.db_config) as conn:
            with conn.transaction():
                n = _propagate_to_duplicates(conn, ctx, batch_id, [])
        print(f"Propagated classifications to {n} copies"
              f" (batch {batch_id}).")
        return
    if not args.csv_path:
        p.error("csv_path is required unless --propagate-only")
    snapshot = load_snapshot(args.project, args.csv_path, args.metadata)
    summary = load_classifications(ctx, snapshot, args.csv_path, model_used=args.model_used)

    print(f"Loaded batch {summary['batch_id']}:")
    print(f"  {summary['comments']} comment classifications")
    print(f"  {summary['topic_rows']} topic rows")
    if summary["skipped_no_phrases"]:
        print(f"  skipped {summary['skipped_no_phrases']} phrase-less topic row(s) (grounding declined)")


if __name__ == "__main__":
    main()
