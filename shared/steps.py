"""The steps, in run order, and the tables each one writes (plan 1; new,
docs/limit-and-jump.md). One registry for the three places that need it: the
console's Steps page, scripts/dump_extract.py and scripts/load_extract.py.

A table can be written by two targets (substance_scores by score, then by
assemble): an extract holds the table as it stood after that target ran.
`fetch` writes files under attachments/ and no table. comment_facts is built
with CREATE TABLE AS and is absent until make facts.
"""

STEPS = [
    ("corpus", ["comment", "attachment_file"]),
    ("dedup", ["comment_dedup"]),
    ("ngrams", ["long_ngrams", "comment_long_ngrams", "long_ngram_stats",
                "long_ngram_processing_log", "duplicate_groups",
                "duplicate_group_members", "duplicate_detection_runs"]),
    ("ner", ["named_entities"]),
    ("tag", ["forests", "roadless_areas", "species", "legal_authority",
             "cited_references", "zipcodes", "entity_scan_state",
             "comment_forests", "comment_areas", "comment_species",
             "comment_authorities", "comment_cited_references", "comment_zipcodes",
             "authority_family"]),
    ("floor", ["substance_floor"]),
    ("groups", ["text_family", "text_family_ngram", "text_family_member",
                "text_family_sentence", "text_family_span",
                "comment_group", "comment_group_member"]),
    ("screen", ["substance_screen"]),
    ("stance", ["classification_runs", "classification_run_items",
                "comment_classification", "classification_topics"]),
    ("score", ["substance_scores", "substance_score_parts", "substance_artifacts"]),
    ("score-rules", ["mf_score_run", "mf_sentence_score", "mf_sentence_hit",
                     "mf_comment_score", "mf_comment_answerability"]),
    ("assemble", ["substance_scores", "substance_score_parts"]),
    ("rate", ["answerability_run", "substance_answerability"]),
    ("fetch", []),
    ("text", ["comment_attachment_text"]),
    ("attachments", ["comment_attachment_text", "comment_attachment_kind",
                     "comment_attachment_count", "comment_organisation"]),
    ("orgs", ["family_organisation"]),
    ("facts", ["comment_facts"]),
]

TARGETS = [target for target, _ in STEPS]
TABLES = dict(STEPS)

# Built by CREATE TABLE AS, so an extract of it is loaded the same way.
CREATED_AS = {"comment_facts"}

# No extract: the corpus is rebuilt from the download the repository ships, and
# the fetch writes files. A jump checks the corpus is loaded and skips the fetch.
NOT_EXTRACTED = {"corpus", "fetch"}


def up_to(target):
    """The targets from the first to `target`, inclusive."""
    if target not in TABLES:
        raise SystemExit(f"no step {target!r}; the steps are: {', '.join(TARGETS)}")
    return TARGETS[:TARGETS.index(target) + 1]


def columns(conn, table, schema="main"):
    """The columns of a table that can be inserted: every one but a generated
    column (classification_topics.phrase_count), which table_xinfo marks hidden."""
    rows = conn.execute(f'PRAGMA "{schema}".table_xinfo("{table}")').fetchall()
    if not rows:
        raise SystemExit(f"{schema}.{table}: no such table")
    return [r["name"] for r in rows if r["hidden"] == 0]
