"""The console's queries. No Streamlit in this module,
so tests/test_console.py can run every query here over a temporary file.

STEPS is the Makefile's targets in run order. For each, the figures that say what
the step has written (label, one-value query) and the breakdowns that say how
(label, query returning rows). COMMENT is what the Comment page shows for one
comment id: one query per table the steps write about it, every ? bound to the id.
"""

STEPS = [
    {
        "target": "schema",
        "what": "the schema and the seeds: the profile, the prompt, the vocabulary",
        "figures": [
            ("topics", "SELECT count(*) FROM topics"),
            ("prompts", "SELECT count(*) FROM prompts"),
            ("vocabulary rows", "SELECT count(*) FROM vocabulary"),
        ],
        "breakdowns": [],
    },
    {
        "target": "corpus",
        "what": "step 1: one row per record of the docket; one row per attachment file",
        "figures": [
            ("records", "SELECT count(*) FROM comment"),
            ("with text", "SELECT count(*) FROM comment WHERE comment_text <> ''"),
            ("withdrawn", "SELECT count(*) FROM comment WHERE withdrawn = 1"),
            ("attachment files", "SELECT count(*) FROM attachment_file"),
        ],
        "breakdowns": [],
    },
    {
        "target": "dedup",
        "what": "step 2: exact and body hashes",
        "figures": [
            ("hashed", "SELECT count(*) FROM comment_dedup"),
            ("originals", "SELECT count(*) FROM comment_dedup WHERE is_original = 1"),
            ("copies", "SELECT count(*) FROM comment_dedup WHERE is_original = 0"),
            ("body originals", "SELECT count(*) FROM comment_dedup WHERE is_middle_original = 1"),
            ("body copies", "SELECT count(*) FROM comment_dedup WHERE is_middle_original = 0"),
        ],
        "breakdowns": [],
    },
    {
        "target": "ngrams",
        "what": "step 2: 6 to 8 word n-grams and the near-duplicate groups at 0.85",
        "figures": [
            ("n-grams", "SELECT count(*) FROM long_ngrams"),
            ("n-gram placements", "SELECT count(*) FROM comment_long_ngrams"),
            ("n-grams with stats", "SELECT count(*) FROM long_ngram_stats"),
            ("near-duplicate groups", "SELECT count(*) FROM duplicate_groups"),
            ("group members", "SELECT count(*) FROM duplicate_group_members"),
        ],
        "breakdowns": [
            ("latest detection run",
             "SELECT run_id, run_timestamp, total_comments_analyzed, near_duplicates,"
             " campaigns, execution_time_seconds"
             " FROM duplicate_detection_runs ORDER BY run_id DESC LIMIT 1"),
        ],
    },
    {
        "target": "ner",
        "what": "step 5: spaCy named entities over the floor's population",
        "figures": [
            ("entities", "SELECT count(*) FROM named_entities"),
            ("comments with entities", "SELECT count(DISTINCT comment_id) FROM named_entities"),
        ],
        "breakdowns": [
            ("by type",
             "SELECT entity_type, count(*) AS n FROM named_entities"
             " GROUP BY entity_type ORDER BY n DESC"),
        ],
    },
    {
        "target": "tag",
        "what": "step 4: the reference lists; the strict and loose dictionary passes",
        "figures": [
            ("forests", "SELECT count(*) FROM forests"),
            ("roadless areas", "SELECT count(*) FROM roadless_areas"),
            ("species", "SELECT count(*) FROM species"),
            ("legal authorities", "SELECT count(*) FROM legal_authority"),
            ("cited references", "SELECT count(*) FROM cited_references"),
            ("zip codes", "SELECT count(*) FROM zipcodes"),
            ("comments scanned, strict",
             "SELECT count(*) FROM entity_scan_state WHERE is_tagged_strict = 1"),
            ("comments scanned, loose",
             "SELECT count(*) FROM entity_scan_state WHERE is_tagged_loose = 1"),
            ("authority families", "SELECT count(*) FROM authority_family"),
        ],
        "breakdowns": [
            ("matches by table and mode",
             "SELECT 'authorities' AS matches, mode, count(*) AS n FROM comment_authorities GROUP BY mode"
             " UNION ALL SELECT 'cited references', mode, count(*) FROM comment_cited_references GROUP BY mode"
             " UNION ALL SELECT 'forests', mode, count(*) FROM comment_forests GROUP BY mode"
             " UNION ALL SELECT 'roadless areas', mode, count(*) FROM comment_areas GROUP BY mode"
             " UNION ALL SELECT 'species', mode, count(*) FROM comment_species GROUP BY mode"
             " UNION ALL SELECT 'zip codes', mode, count(*) FROM comment_zipcodes GROUP BY mode"),
        ],
    },
    {
        "target": "floor",
        "what": "step 6: the floor filter",
        "figures": [
            ("analysed", "SELECT count(*) FROM substance_floor"),
            ("floored", "SELECT count(*) FROM substance_floor WHERE floored = 1"),
            ("survivors", "SELECT count(*) FROM substance_floor WHERE floored = 0"),
        ],
        "breakdowns": [
            ("the four detectors",
             "SELECT sum(has_entity) AS has_entity, sum(has_citation) AS has_citation,"
             " sum(has_deficiency) AS has_deficiency, sum(has_firstperson) AS has_firstperson"
             " FROM substance_floor"),
        ],
    },
    {
        "target": "groups",
        "what": "step 2: the text families and the comment-group partition",
        "figures": [
            ("text families", "SELECT count(*) FROM text_family"),
            ("campaign families", "SELECT count(*) FROM text_family WHERE is_campaign = 1"),
            ("family members", "SELECT count(*) FROM text_family_member"),
            ("members with own text",
             "SELECT count(*) FROM text_family_member WHERE has_own_text = 1"),
            ("comment groups", "SELECT count(*) FROM comment_group"),
            ("group members", "SELECT count(*) FROM comment_group_member"),
        ],
        "breakdowns": [
            ("groups by kind",
             "SELECT group_kind, count(*) AS groups, sum(size) AS comments"
             " FROM comment_group GROUP BY group_kind ORDER BY comments DESC"),
        ],
    },
    {
        "target": "screen",
        "what": "step 6: the mechanical screens",
        "figures": [
            ("screened", "SELECT count(*) FROM substance_screen"),
        ],
        "breakdowns": [
            ("by class",
             "SELECT screen_class, count(*) AS n FROM substance_screen"
             " GROUP BY screen_class ORDER BY screen_class"),
        ],
    },
    {
        "target": "stance",
        "what": "step 3 (model): one classification per comment group, copied to the members",
        "figures": [
            ("runs", "SELECT count(*) FROM classification_runs"),
            ("groups to classify", "SELECT count(*) FROM comment_group"),
            ("active classifications",
             "SELECT count(*) FROM comment_classification WHERE is_active = 1"),
            ("active topic rows",
             "SELECT count(*) FROM classification_topics WHERE is_active = 1"),
        ],
        "breakdowns": [
            ("latest run",
             "SELECT run_timestamp, model_name, comment_count, created_at"
             " FROM classification_runs ORDER BY run_timestamp DESC LIMIT 1"),
            ("latest run's items by status",
             "SELECT run_id, status, count(*) AS groups, sum(prompt_tokens) AS tokens_in,"
             " sum(completion_tokens) AS tokens_out, round(sum(seconds)) AS seconds"
             " FROM classification_run_items"
             " WHERE run_id = (SELECT max(run_id) FROM classification_run_items)"
             " GROUP BY run_id, status"),
            ("latest run's errors by kind",
             "SELECT error_kind, count(*) AS n FROM classification_run_items"
             " WHERE run_id = (SELECT max(run_id) FROM classification_run_items)"
             " AND status = 'error' GROUP BY error_kind"),
            ("stance of the active classifications",
             "SELECT s.sentiment, count(*) AS n FROM comment_classification cc"
             " JOIN sentiment s USING (sentiment_id) WHERE cc.is_active = 1"
             " GROUP BY s.sentiment ORDER BY n DESC"),
        ],
    },
    {
        "target": "score-model",
        "what": "step 6 (model): the v3 substance reading over class A",
        "figures": [
            ("class A to read",
             "SELECT count(*) FROM substance_screen WHERE screen_class = 'A'"),
            ("scored", "SELECT count(*) FROM substance_scores"),
            ("read directly", "SELECT count(*) FROM substance_scores WHERE scored_via = 'direct'"),
        ],
        "breakdowns": [
            ("by how the score was reached",
             "SELECT scored_via, instrument_version, count(*) AS n,"
             " sum(tokens_in) AS tokens_in, sum(tokens_out) AS tokens_out"
             " FROM substance_scores GROUP BY scored_via, instrument_version"),
            ("by band",
             "SELECT band, count(*) AS n FROM substance_scores GROUP BY band ORDER BY n DESC"),
        ],
    },
    {
        "target": "score-model-free",
        "what": "step 6 (rules): the model-free reading of the same class A, no model call",
        "figures": [
            ("class A to read",
             "SELECT count(*) FROM substance_screen WHERE screen_class = 'A'"),
            ("scored by the rules", "SELECT count(*) FROM mf_comment_score"),
            ("gate open", "SELECT count(*) FROM mf_comment_score WHERE gate = 1"),
        ],
        "breakdowns": [
            ("by band",
             "SELECT ruleset_version, band, count(*) AS n FROM mf_comment_score"
             " GROUP BY ruleset_version, band ORDER BY n DESC"),
            ("answerability by level",
             "SELECT level, count(*) AS n FROM mf_comment_answerability GROUP BY level ORDER BY level"),
            ("the rules that fired most",
             "SELECT rule, count(*) AS n FROM mf_sentence_hit GROUP BY rule ORDER BY n DESC LIMIT 25"),
        ],
    },
    {
        "target": "assemble",
        "what": "step 6: campaign inheritance and the delta rows; LAW from the citations",
        "figures": [
            ("exemplar readings", "SELECT count(*) FROM substance_scores WHERE scored_via = 'exemplar'"),
            ("delta readings", "SELECT count(*) FROM substance_scores WHERE scored_via = 'delta'"),
            ("inherited", "SELECT count(*) FROM substance_scores WHERE scored_via = 'inherited'"),
            ("score parts", "SELECT count(*) FROM substance_score_parts"),
            ("law scored", "SELECT count(*) FROM substance_scores WHERE law IS NOT NULL"),
        ],
        "breakdowns": [
            ("parts by kind",
             "SELECT part, count(*) AS n FROM substance_score_parts GROUP BY part"),
        ],
    },
    {
        "target": "rate",
        "what": "step 7: the answerability rating",
        "figures": [
            ("rating runs", "SELECT count(*) FROM answerability_run"),
            ("rated", "SELECT count(*) FROM substance_answerability"),
        ],
        "breakdowns": [
            ("latest run by level",
             "SELECT a_level, count(*) AS n FROM substance_answerability"
             " WHERE run_id = (SELECT max(run_id) FROM answerability_run)"
             " GROUP BY a_level ORDER BY a_level"),
        ],
    },
    {
        "target": "fetch",
        "what": "step 8: every attachment file fetched from regulations.gov into attachments/;"
                " steps 1 to 7 read none of them",
        "figures": [],
        "breakdowns": [],
    },
    {
        "target": "text",
        "what": "step 8: the text of every fetched file",
        "figures": [
            ("files with a text row", "SELECT count(*) FROM comment_attachment_text"),
            ("comments with one", "SELECT count(DISTINCT comment_id) FROM comment_attachment_text"),
        ],
        "breakdowns": [
            ("renditions",
             "SELECT count(pdf_text) AS pdf, sum(pdf_ocr) AS pdf_by_ocr, count(docx_text) AS docx,"
             " count(rtf_text) AS rtf, count(txt_text) AS txt FROM comment_attachment_text"),
        ],
    },
    {
        "target": "attachments",
        "what": "step 8: the kind of every file; the OCR; what each comment counts as; the roster (model)",
        "figures": [
            ("files with a kind", "SELECT count(*) FROM comment_attachment_kind"),
            ("pdf files read by OCR", "SELECT count(*) FROM comment_attachment_text WHERE pdf_ocr = 1"),
            ("comments counted", "SELECT count(*) FROM comment_attachment_count"),
            ("letters read for the roster", "SELECT count(*) FROM comment_organisation"),
        ],
        "breakdowns": [
            ("files by kind",
             "SELECT kind, count(*) AS n FROM comment_attachment_kind GROUP BY kind ORDER BY n DESC"),
            ("comments by the basis of their count",
             "SELECT basis, count(*) AS comments, sum(counts_as) AS counts_as"
             " FROM comment_attachment_count GROUP BY basis"),
            ("the roster by sender and stance",
             "SELECT sender_kind, stance, count(*) AS n FROM comment_organisation"
             " GROUP BY sender_kind, stance ORDER BY n DESC"),
        ],
    },
    {
        "target": "orgs",
        "what": "step 9: who ran each campaign, on four bases",
        "figures": [
            ("campaign families", "SELECT count(*) FROM text_family WHERE is_campaign = 1"),
            ("families with an organisation", "SELECT count(*) FROM family_organisation"),
        ],
        "breakdowns": [
            ("by basis",
             "SELECT basis, count(*) AS n FROM family_organisation GROUP BY basis ORDER BY n DESC"),
        ],
    },
    {
        "target": "facts",
        "what": "one row per comment: comment_facts (built with CREATE TABLE AS; absent until then)",
        "figures": [
            ("rows", "SELECT count(*) FROM comment_facts"),
        ],
        "breakdowns": [],
    },
    {
        "target": "sentences",
        "what": "step 10, the sentences of the comments whose model-free gate is open, for the clusters",
        "figures": [
            ("builds", "SELECT count(*) FROM gate_sentence_run"),
            ("sentences (occurrences)", "SELECT count(*) FROM gate_sentence_occurrence"),
            ("distinct sentences", "SELECT count(*) FROM gate_sentence"),
            ("that open the gate alone", "SELECT count(*) FROM gate_sentence WHERE opens = 1"),
            ("that hold a whole-comment gate hit", "SELECT count(*) FROM gate_sentence WHERE holds_hit = 1"),
        ],
        "breakdowns": [
            ("the latest build",
             "SELECT run_id, classes, gate_comments, occurrences, distinct_sentences, comments_opening,"
             " comments_hit, comments_neither, sentences_unlocated, hits_unlocated, created_at"
             " FROM gate_sentence_run ORDER BY run_id DESC LIMIT 1"),
        ],
    },
    {
        "target": "embed",
        "what": "step 11, one vector for each distinct sentence, by model and instruction",
        "figures": [
            ("vectors", "SELECT count(*) FROM sentence_embedding"),
        ],
        "breakdowns": [
            ("by model and view",
             "SELECT model, CASE instruction WHEN '' THEN '(plain text)' ELSE instruction END AS instruction,"
             " count(*) AS vectors, max(created_at) AS latest FROM sentence_embedding GROUP BY model, instruction"),
        ],
    },
    {
        "target": "clusters",
        "what": "steps 12 to 14, the clustering cases: clusters, topics and their names (the Topics page reads them)",
        "figures": [
            ("cases", "SELECT count(*) FROM cluster_case"),
            ("clusters, all cases", "SELECT count(*) FROM cluster_case_cluster"),
            ("topics, all cases", "SELECT count(*) FROM cluster_case_topic"),
        ],
        "breakdowns": [
            ("the cases",
             "SELECT case_name, clusters, topics, leaders, leaders_clustered, comments_unclustered, gate_comments,"
             " created_at FROM cluster_case ORDER BY created_at"),
        ],
    },
    {
        "target": "docindex",
        "what": "the record documents: their sections, chunks and chunk vectors (docs/docindex.md)",
        "figures": [
            ("documents", "SELECT count(*) FROM doc_documents"),
            ("sections", "SELECT count(*) FROM doc_sections"),
            ("chunks", "SELECT count(*) FROM doc_chunks"),
            ("chunk vectors", "SELECT count(*) FROM doc_chunk_embeddings"),
        ],
        "breakdowns": [
            ("the documents",
             "SELECT d.title, d.source_file, count(DISTINCT s.section_id) AS sections,"
             " count(c.chunk_id) AS chunks, d.ingested_at FROM doc_documents d"
             " LEFT JOIN doc_sections s USING (document_id)"
             " LEFT JOIN doc_chunks c USING (section_id)"
             " GROUP BY d.document_id ORDER BY d.title"),
        ],
    },
    {
        "target": "retrieve",
        "what": "the K nearest record chunks per gate-opening sentence, by cosine (docs/retrieval.md)",
        "figures": [
            ("pairs", "SELECT count(*) FROM doc_retrieval"),
            ("sentences", "SELECT count(DISTINCT text_key) FROM doc_retrieval"),
        ],
        "breakdowns": [
            ("by document, first-ranked chunks",
             "SELECT d.title, count(*) AS first_hits, round(avg(r.cosine), 4) AS mean_cosine"
             " FROM doc_retrieval r JOIN doc_chunks c ON c.chunk_id = r.chunk_id"
             " JOIN doc_sections s USING (section_id) JOIN doc_documents d USING (document_id)"
             " WHERE r.rank = 1 GROUP BY d.document_id ORDER BY first_hits DESC"),
        ],
    },
    {
        "target": "nli",
        "what": "the cross-encoder's reading of the near pairs, and the retrieval labels (docs/retrieval.md)",
        "figures": [
            ("pairs read", "SELECT count(*) FROM doc_nli"),
            ("sentence labels", "SELECT count(*) FROM doc_sentence_label"),
            ("comment labels", "SELECT count(*) FROM doc_comment_label"),
        ],
        "breakdowns": [
            ("comments by label",
             "SELECT label, count(*) AS comments FROM doc_comment_label"
             " GROUP BY label ORDER BY comments DESC"),
            ("sentences by label",
             "SELECT label, count(*) AS sentences FROM doc_sentence_label"
             " GROUP BY label ORDER BY sentences DESC"),
        ],
    },
]

# The Comment page: (title, query); every ? is the comment id.
COMMENT = [
    ("comment", "SELECT * FROM comment WHERE comment_id = ?"),
    ("attachment files",
     "SELECT ordinal, format, url FROM attachment_file WHERE comment_id = ? ORDER BY ordinal, format"),
    ("copies (comment_dedup)", "SELECT * FROM comment_dedup WHERE comment_id = ?"),
    ("near-duplicate group",
     "SELECT g.group_id, g.group_size, m.is_representative"
     " FROM duplicate_group_members m JOIN duplicate_groups g USING (group_id)"
     " WHERE m.comment_id = ?"),
    ("text family",
     "SELECT m.*, f.core_kind, f.n_texts, f.n_comments, f.is_campaign, f.exemplar_comment_id"
     " FROM text_family_member m JOIN text_family f USING (family_id) WHERE m.comment_id = ?"),
    ("comment group", "SELECT * FROM v_comment_group_member WHERE comment_id = ?"),
    ("stance (active)",
     "SELECT cc.classification_id, s.sentiment, cc.sentiment_strength, cc.confidence_score,"
     " cc.batch_id, cc.model_version, cc.processed_date, cc.notes"
     " FROM comment_classification cc JOIN sentiment s USING (sentiment_id)"
     " WHERE cc.comment_id = ? AND cc.is_active = 1"),
    ("topics (active)",
     "SELECT t.topic_name, ct.confidence, ct.rank_order, ct.supporting_phrases"
     " FROM classification_topics ct JOIN comment_classification cc USING (classification_id)"
     " JOIN topics t USING (topic_id)"
     " WHERE cc.comment_id = ? AND cc.is_active = 1 AND ct.is_active = 1 ORDER BY ct.rank_order"),
    ("entity scan state", "SELECT * FROM entity_scan_state WHERE comment_id = ?"),
    ("entities (step 4)",
     "SELECT 'authority' AS kind, citation AS value, matched_text, mode FROM comment_authorities WHERE comment_id = ?"
     " UNION ALL SELECT 'cited reference', citation_key, matched_text, mode FROM comment_cited_references WHERE comment_id = ?"
     " UNION ALL SELECT 'forest', forest_name, matched_text, mode FROM comment_forests WHERE comment_id = ?"
     " UNION ALL SELECT 'roadless area', area_name, matched_text, mode FROM comment_areas WHERE comment_id = ?"
     " UNION ALL SELECT 'species', species_name, matched_text, mode FROM comment_species WHERE comment_id = ?"
     " UNION ALL SELECT 'zip code', zipcode, matched_text, mode FROM comment_zipcodes WHERE comment_id = ?"),
    ("named entities (step 5)",
     "SELECT entity_type, entity_text, char_start, char_end FROM named_entities"
     " WHERE comment_id = ? ORDER BY char_start"),
    ("floor", "SELECT * FROM substance_floor WHERE comment_id = ?"),
    ("screen", "SELECT * FROM substance_screen WHERE comment_id = ?"),
    ("substance score", "SELECT * FROM substance_scores WHERE comment_id = ?"),
    ("score parts", "SELECT * FROM substance_score_parts WHERE comment_id = ?"),
    ("answerability", "SELECT * FROM v_substance_answerability WHERE comment_id = ?"),
    ("attachment text",
     "SELECT attachment_id, title, formats, pdf_chars, pdf_pages, pdf_ocr, docx_chars, rtf_chars,"
     " txt_chars, extracted_at FROM comment_attachment_text WHERE comment_id = ?"),
    ("attachment kind", "SELECT * FROM comment_attachment_kind WHERE comment_id = ?"),
    ("attachment count", "SELECT * FROM comment_attachment_count WHERE comment_id = ?"),
    ("organisation (roster)", "SELECT * FROM comment_organisation WHERE comment_id = ?"),
    ("campaign organisation",
     "SELECT fo.* FROM family_organisation fo JOIN text_family_member m USING (family_id)"
     " WHERE m.comment_id = ?"),
    ("comparison readings (make score-model-compare)",
     "SELECT run_id, method, error, record FROM score_compare_reading"
     " WHERE comment_id = ? ORDER BY run_id, method"),
]

# The Compare page: every make score-model-compare run, newest first, with the
# code it ran and how many readings it kept; and one run's readings.
COMPARE_RUNS = (
    "SELECT r.run_id, r.started_at, r.finished_at, substr(r.code_version, 1, 12) AS git_commit,"
    " r.code_dirty AS uncommitted_changes, r.model, r.server, r.instrument_version,"
    " r.ruleset_version, r.comments_of, r.pool, r.picked,"
    " (SELECT count(*) FROM score_compare_reading x WHERE x.run_id = r.run_id"
    "   AND x.method = 'model' AND x.record IS NOT NULL) AS model_readings,"
    " (SELECT count(*) FROM score_compare_reading x WHERE x.run_id = r.run_id"
    "   AND x.method = 'model-free' AND x.record IS NOT NULL) AS rules_readings,"
    " (SELECT count(*) FROM score_compare_reading x WHERE x.run_id = r.run_id"
    "   AND x.error IS NOT NULL) AS errors"
    " FROM score_compare_run r ORDER BY r.run_id DESC")
COMPARE_READINGS = ("SELECT comment_id, method, record, error FROM score_compare_reading"
                    " WHERE run_id = ? ORDER BY comment_id, method")

TABLES = ("SELECT type, name FROM sqlite_master WHERE type IN ('table', 'view')"
          " AND name NOT LIKE 'sqlite_%' ORDER BY type, name")

# ---------------------------------------------------------------- results
# The results pages (console/results.py): what the analysis found, aggregated
# over the corpus. Every query here runs on the schema in tests/test_console.py;
# the ones with a ? take the parameters named beside them.

# Overview, and the Coordination page: the records, and the comment-group
# partition (one group is one letter: a unique comment, or every copy of one).
RECORDS = ("SELECT count(*) AS records, coalesce(sum(comment_text <> ''), 0) AS with_text,"
           " coalesce(sum(withdrawn), 0) AS withdrawn,"
           " coalesce(sum(comment_text = '' AND withdrawn = 0), 0) AS blank FROM comment")
GROUPS_BY_KIND = (
    "SELECT g.group_kind AS kind, v.label, v.meaning, count(*) AS letters, sum(g.size) AS comments"
    " FROM comment_group g LEFT JOIN vocabulary v ON v.kind = 'group_kind' AND v.code = g.group_kind"
    " GROUP BY g.group_kind ORDER BY v.ordinal")

# Stance and topics: the active classification of every comment (make stance
# classifies one comment per group and copies it to the group's members).
STANCE = (
    "SELECT s.sentiment AS stance, s.meaning, count(*) AS comments, count(DISTINCT m.group_id) AS letters"
    " FROM comment_classification cc JOIN sentiment s USING (sentiment_id)"
    " LEFT JOIN comment_group_member m ON m.comment_id = cc.comment_id"
    " WHERE cc.is_active = 1 GROUP BY s.sentiment ORDER BY comments DESC")
STANCE_STRENGTH = (
    "SELECT s.sentiment AS stance, cc.sentiment_strength AS strength, count(*) AS comments"
    " FROM comment_classification cc JOIN sentiment s USING (sentiment_id)"
    " WHERE cc.is_active = 1 GROUP BY 1, 2")
TOPICS = (
    "SELECT t.topic_name AS topic, t.description, count(*) AS comments,"
    " count(DISTINCT m.group_id) AS letters, round(avg(ct.confidence), 3) AS avg_confidence"
    " FROM classification_topics ct JOIN topics t USING (topic_id)"
    " JOIN comment_classification cc ON cc.classification_id = ct.classification_id AND cc.is_active = 1"
    " LEFT JOIN comment_group_member m ON m.comment_id = cc.comment_id"
    " WHERE ct.is_active = 1 GROUP BY t.topic_name ORDER BY comments DESC")
STANCE_BY_TOPIC = (
    "SELECT t.topic_name AS topic, s.sentiment AS stance, count(*) AS comments"
    " FROM classification_topics ct JOIN topics t USING (topic_id)"
    " JOIN comment_classification cc ON cc.classification_id = ct.classification_id AND cc.is_active = 1"
    " JOIN sentiment s ON s.sentiment_id = cc.sentiment_id"
    " WHERE ct.is_active = 1 GROUP BY 1, 2")
TOPIC_PAIRS = (
    "SELECT ta.topic_name AS topic_a, tb.topic_name AS topic_b, count(*) AS comments"
    " FROM classification_topics ca"
    " JOIN comment_classification cc ON cc.classification_id = ca.classification_id AND cc.is_active = 1"
    " JOIN classification_topics cb ON cb.classification_id = ca.classification_id"
    "  AND cb.is_active = 1 AND cb.topic_id > ca.topic_id"
    " JOIN topics ta ON ta.topic_id = ca.topic_id JOIN topics tb ON tb.topic_id = cb.topic_id"
    " WHERE ca.is_active = 1 GROUP BY 1, 2")
STANCE_BY_DAY = (
    "SELECT substr(c.received_date, 1, 10) AS day, s.sentiment AS stance, count(*) AS comments"
    " FROM comment_classification cc JOIN comment c USING (comment_id)"
    " JOIN sentiment s ON s.sentiment_id = cc.sentiment_id"
    " WHERE cc.is_active = 1 AND c.received_date IS NOT NULL GROUP BY 1, 2 ORDER BY 1")
POSTED_RECEIVED = (
    "SELECT substr(posted_date, 1, 10) AS day, 'Posted' AS series, count(*) AS comments"
    " FROM v_source_comments WHERE posted_date IS NOT NULL GROUP BY 1"
    " UNION ALL SELECT substr(received_date, 1, 10), 'Received', count(*)"
    " FROM v_source_comments WHERE received_date IS NOT NULL GROUP BY 1 ORDER BY 1")
# One topic's letters, most-sent first: ? = topic, stance or '' for any (twice),
# limit, offset; and how many there are.
_TOPIC_LETTERS_FROM = (
    " FROM classification_topics ct JOIN topics t USING (topic_id)"
    " JOIN comment_classification cc ON cc.classification_id = ct.classification_id AND cc.is_active = 1"
    " JOIN sentiment s ON s.sentiment_id = cc.sentiment_id"
    " JOIN comment_group_member m ON m.comment_id = cc.comment_id"
    " JOIN comment_group g ON g.group_id = m.group_id AND g.canonical_comment_id = cc.comment_id"
    " WHERE ct.is_active = 1 AND t.topic_name = ? AND (? = '' OR s.sentiment = ?)")
TOPIC_LETTER_COUNT = "SELECT count(*) AS n" + _TOPIC_LETTERS_FROM
TOPIC_LETTERS = (
    "SELECT cc.comment_id, s.sentiment AS stance, cc.sentiment_strength AS strength,"
    " ct.confidence, ct.supporting_phrases, g.group_kind, g.size,"
    " (SELECT comment_text FROM comment c WHERE c.comment_id = cc.comment_id) AS comment_text"
    + _TOPIC_LETTERS_FROM +
    " ORDER BY g.size DESC, ct.confidence DESC, cc.comment_id LIMIT ? OFFSET ?")

# Coordination: the copies, the campaigns, the daily wave.
COPIES = (
    "SELECT count(*) AS hashed, coalesce(sum(is_original = 0), 0) AS exact_copies,"
    " coalesce(sum(is_original = 1 AND is_middle_original = 0), 0) AS same_body FROM comment_dedup")
CAMPAIGNS = (
    "SELECT f.family_id, f.n_comments AS comments, f.n_texts AS texts, f.core_kind,"
    " (SELECT count(*) FROM text_family_member x WHERE x.family_id = f.family_id AND x.has_own_text = 1)"
    "   AS with_own_text,"
    " fo.organisation, v.label AS organisation_basis, s.sentiment AS stance,"
    " f.exemplar_comment_id, c.comment_text"
    " FROM text_family f JOIN comment c ON c.comment_id = f.exemplar_comment_id"
    " LEFT JOIN family_organisation fo ON fo.family_id = f.family_id"
    " LEFT JOIN vocabulary v ON v.kind = 'organisation_basis' AND v.code = fo.basis"
    " LEFT JOIN comment_classification cc ON cc.comment_id = f.exemplar_comment_id AND cc.is_active = 1"
    " LEFT JOIN sentiment s ON s.sentiment_id = cc.sentiment_id"
    " WHERE f.is_campaign = 1 ORDER BY f.n_comments DESC")
DAILY_WAVE = (
    "SELECT substr(c.received_date, 1, 10) AS day,"
    " sum(v.rep_comment_id = c.comment_id) AS unique_letters,"
    " sum(v.rep_comment_id <> c.comment_id) AS repeated"
    " FROM v_source_comments c JOIN v_comment_representative v USING (comment_id)"
    " WHERE c.received_date IS NOT NULL GROUP BY 1 ORDER BY 1")

# Places and citations: the strict (exact-match) layer of make tag. Each kind:
# its table, its value column, the label.
TAGS = {
    "forest": ("comment_forests", "forest_name", "Name a national forest"),
    "roadless area": ("comment_areas", "area_name", "Name a roadless area"),
    "species": ("comment_species", "species_name", "Name a species"),
    "legal authority": ("comment_authorities", "family_key", "Cite a legal authority"),
    "cited reference": ("comment_cited_references", "citation_key", "Cite a reference"),
    "zip code": ("comment_zipcodes", "zipcode", "Give a zip code"),
}


def tag_comments(kind):
    table, _, _ = TAGS[kind]
    return f"SELECT count(DISTINCT comment_id) FROM {table} WHERE mode = 'strict'"


def tag_top(kind):
    """Each value of a kind with the comments and the letters that name it."""
    table, col, _ = TAGS[kind]
    return (f"SELECT t.{col} AS value, count(DISTINCT t.comment_id) AS comments,"
            f" count(DISTINCT m.group_id) AS letters"
            f" FROM {table} t LEFT JOIN comment_group_member m ON m.comment_id = t.comment_id"
            f" WHERE t.mode = 'strict' GROUP BY t.{col} ORDER BY comments DESC, value")


def tag_letters(kind):
    """The letters that name one value (?), most-sent first: per comment group,
    how many of its comments name it, the words as written, and the text of the
    first one."""
    table, col, _ = TAGS[kind]
    return ("SELECT x.*, c.comment_text FROM ("
            f" SELECT g.group_id, g.group_kind, g.size, count(DISTINCT t.comment_id) AS naming,"
            f" min(t.comment_id) AS comment_id, group_concat(DISTINCT t.matched_text) AS as_written"
            f" FROM {table} t JOIN comment_group_member m ON m.comment_id = t.comment_id"
            f" JOIN comment_group g ON g.group_id = m.group_id"
            f" WHERE t.mode = 'strict' AND t.{col} = ? GROUP BY g.group_id) x"
            " JOIN comment c USING (comment_id) ORDER BY x.naming DESC, x.comment_id LIMIT 100")


_NO_TAG = " AND ".join(f"NOT EXISTS (SELECT 1 FROM {t} x WHERE x.comment_id = s.comment_id)"
                       for t, _, _ in TAGS.values())
NAMES_NOTHING = ("SELECT count(*) FROM v_source_comments s JOIN entity_scan_state e USING (comment_id)"
                 f" WHERE e.is_tagged_strict = 1 AND {_NO_TAG}")
# ? = how many, drawn at random
NAMES_NOTHING_SAMPLE = ("SELECT s.comment_id, s.comment_text FROM v_source_comments s"
                        " JOIN entity_scan_state e USING (comment_id)"
                        f" WHERE e.is_tagged_strict = 1 AND {_NO_TAG} ORDER BY random() LIMIT ?")
AREAS = (
    "SELECT a.area_name || CASE WHEN count(DISTINCT r.forest) = 1 THEN ' (' || min(r.forest) || ')'"
    " ELSE '' END AS area, count(DISTINCT a.comment_id) AS comments"
    " FROM comment_areas a JOIN roadless_areas r ON r.name = a.area_name"
    " WHERE a.mode = 'strict' GROUP BY a.area_name ORDER BY comments DESC LIMIT 25")
STATES = ("SELECT state, count(DISTINCT comment_id) AS comments FROM comment_zipcodes"
          " WHERE mode = 'strict' AND state IS NOT NULL AND city IS NOT NULL"
          " GROUP BY 1 ORDER BY 2 DESC")
AUTHORITY_FAMILIES = (
    "SELECT a.family_key AS family,"
    " CASE WHEN f.canonical = 1 THEN 'in the agency record' ELSE 'brought by commenters' END AS origin,"
    " count(DISTINCT a.comment_id) AS comments, count(DISTINCT a.citation) AS variants"
    " FROM comment_authorities a LEFT JOIN authority_family f USING (family_key)"
    " WHERE a.mode = 'strict' GROUP BY a.family_key ORDER BY comments DESC, family")
AUTHORITY_VARIANTS = (
    "SELECT family_key AS family, citation AS as_written, count(DISTINCT comment_id) AS comments"
    " FROM comment_authorities WHERE mode = 'strict' GROUP BY 1, 2 ORDER BY 1, 3 DESC")
# Each cited reference resolved to its reference row, the agency's (seeded) row first.
_CITED = ("WITH t AS (SELECT t.comment_id, t.citation_key,"
          "  (SELECT c.id FROM cited_references c WHERE c.citation_key = t.citation_key"
          "   OR c.display = t.citation_key ORDER BY c.seed_id IS NULL LIMIT 1) AS ref_id"
          "  FROM comment_cited_references t WHERE t.mode = 'strict')")
_ORIGIN = "CASE WHEN cr.seed_id IS NOT NULL THEN 'in the agency record' ELSE 'brought by commenters' END"
BIBLIOGRAPHY_ORIGINS = (
    _CITED + f" SELECT {_ORIGIN} AS origin, count(DISTINCT coalesce(cr.display, t.citation_key)) AS works,"
    " count(DISTINCT t.comment_id) AS comments"
    " FROM t LEFT JOIN cited_references cr ON cr.id = t.ref_id GROUP BY 1 ORDER BY 1 DESC")
BIBLIOGRAPHY = (
    _CITED +
    " SELECT count(DISTINCT t.comment_id) AS comments, coalesce(cr.display, t.citation_key) AS reference,"
    " cr.title, cr.authors, cr.year, cr.type, cr.url,"
    f" {_ORIGIN} AS origin"
    " FROM t LEFT JOIN cited_references cr ON cr.id = t.ref_id"
    " GROUP BY 2, 3, 4, 5, 6, 7, 8 ORDER BY comments DESC, reference")

# Substance: the floor, the screen, and the two readings (class A, and any other
# screen class make score-model-free was asked for), one row per comment in one
# shape, with the comment's screen class. ? on the rules' reading = the rule set; on the model's,
# the answerability run (NULL for none).
FLOOR = ("SELECT count(*) AS analysed, coalesce(sum(floored), 0) AS floored,"
         " coalesce(sum(1 - floored), 0) AS survivors, coalesce(sum(has_entity), 0) AS has_entity,"
         " coalesce(sum(has_citation), 0) AS has_citation, coalesce(sum(has_deficiency), 0) AS has_deficiency,"
         " coalesce(sum(has_firstperson), 0) AS has_firstperson FROM substance_floor")
SCREEN = ("SELECT screen_class, count(*) AS comments, sum(authority) AS authority, sum(reference) AS reference,"
          " sum(doc_cite) AS doc_cite, sum(deficiency) AS deficiency, sum(action_ref) AS action_ref,"
          " sum(evid_ner) AS evid_ner FROM substance_screen GROUP BY 1 ORDER BY 1")
_READING_CONTEXT = (
    " LEFT JOIN comment_group_member m ON m.comment_id = s.comment_id"
    " LEFT JOIN comment_group g ON g.group_id = m.group_id"
    " LEFT JOIN comment_classification cc ON cc.comment_id = s.comment_id AND cc.is_active = 1"
    " LEFT JOIN sentiment st ON st.sentiment_id = cc.sentiment_id"
    " LEFT JOIN substance_screen sc ON sc.comment_id = s.comment_id")
RULESETS = "SELECT DISTINCT ruleset_version FROM mf_comment_score ORDER BY 1"
RULES_READING = (
    "SELECT s.comment_id, s.place, s.stand, s.doc, s.gap, s.evid, s.ask, s.alt, s.law, s.strength, s.gate,"
    " s.gate_basis, s.band, a.level AS a_level, 'direct' AS scored_via,"
    " g.group_id, g.group_kind, g.size, st.sentiment AS stance, sc.screen_class"
    " FROM mf_comment_score s"
    " LEFT JOIN mf_comment_answerability a ON a.ruleset_version = s.ruleset_version AND a.comment_id = s.comment_id"
    + _READING_CONTEXT + " WHERE s.ruleset_version = ?")
ANSWERABILITY_RUNS = ("SELECT run_id, rater, evidence, weights_version, instrument_version, created_at"
                      " FROM answerability_run ORDER BY run_id DESC")
MODEL_READING = (
    "SELECT s.comment_id, s.place, s.stand, s.doc, s.gap, s.evid, s.ask, s.alt, s.law, s.strength, s.gate,"
    " s.gate_basis, s.band, a.a_level, s.scored_via,"
    " g.group_id, g.group_kind, g.size, st.sentiment AS stance, sc.screen_class"
    " FROM substance_scores s"
    " LEFT JOIN substance_answerability a ON a.comment_id = s.comment_id AND a.run_id = ?"
    + _READING_CONTEXT)
# The rules that put each dimension where it is, over every comment the rules
# read: GAP's from the sentences, the rest from the whole comment (the hybrid
# score's evidence, model_free/run.py json_record). ? = the rule set.
RULES_FIRED = (
    "SELECT h.dimension, h.grade, h.rule, count(DISTINCT u.comment_id) AS comments, count(*) AS hits"
    " FROM mf_sentence_hit h JOIN mf_sentence_score u"
    "  ON u.ruleset_version = h.ruleset_version AND u.unit_id = h.unit_id"
    " WHERE h.ruleset_version = ? AND (h.dimension = 'GAP') = (h.unit_id > 0)"
    " GROUP BY 1, 2, 3 ORDER BY comments DESC")
# One comment's evidence under the rules: ? = the rule set, the comment id.
RULES_EVIDENCE = (
    "SELECT h.dimension, h.grade, h.rule, h.match FROM mf_sentence_hit h"
    " JOIN mf_sentence_score u ON u.ruleset_version = h.ruleset_version AND u.unit_id = h.unit_id"
    " WHERE h.ruleset_version = ? AND u.comment_id = ? AND (h.dimension = 'GAP') = (h.unit_id > 0)"
    " ORDER BY h.dimension, h.grade DESC, h.unit_id, h.start_char")
# One comment's model reading beyond its levels: ? = the comment id.
MODEL_DETAIL = ("SELECT scored_via, exemplar_id, model, instrument_version, rationale"
                " FROM substance_scores WHERE comment_id = ?")
# One comment's text and its place in the analysis: ? = the comment id.
COMMENT_CARD = (
    "SELECT c.comment_id, c.comment_text, c.posted_date, c.received_date, c.title,"
    " s.sentiment AS stance, s.meaning AS stance_meaning, cc.sentiment_strength AS stance_strength,"
    " g.group_kind, g.size, g.canonical_comment_id, f.family_id, f.is_campaign, fo.organisation,"
    " sc.screen_class"
    " FROM comment c"
    " LEFT JOIN comment_classification cc ON cc.comment_id = c.comment_id AND cc.is_active = 1"
    " LEFT JOIN sentiment s ON s.sentiment_id = cc.sentiment_id"
    " LEFT JOIN comment_group_member m ON m.comment_id = c.comment_id"
    " LEFT JOIN comment_group g ON g.group_id = m.group_id"
    " LEFT JOIN text_family_member fm ON fm.comment_id = c.comment_id"
    " LEFT JOIN text_family f ON f.family_id = fm.family_id"
    " LEFT JOIN family_organisation fo ON fo.family_id = f.family_id"
    " LEFT JOIN substance_screen sc ON sc.comment_id = c.comment_id"
    " WHERE c.comment_id = ?")
COMMENT_TOPICS = (
    "SELECT t.topic_name AS topic, ct.confidence, ct.supporting_phrases"
    " FROM classification_topics ct JOIN comment_classification cc USING (classification_id)"
    " JOIN topics t USING (topic_id)"
    " WHERE cc.comment_id = ? AND cc.is_active = 1 AND ct.is_active = 1 ORDER BY ct.rank_order")
COMMENT_NAMES = " UNION ALL ".join(
    f"SELECT '{kind}' AS kind, {col} AS value, group_concat(DISTINCT matched_text) AS as_written"
    f" FROM {table} WHERE comment_id = ? AND mode = 'strict' GROUP BY {col}"
    for kind, (table, col, _) in TAGS.items())


# ------------------------------------------------------------ the Topics page
# The sentences of the gate set (make sentences), and the clustering cases
# (make clusters): every case with its measures; one case's topics; one topic's
# clusters; one cluster's sentences and comments; one case's noise.

SENTENCE_RUN = """
SELECT run_id, classes, gate_comments, occurrences, distinct_sentences, comments_opening, comments_hit,
       comments_neither, sentences_unlocated, hits_unlocated, created_at
FROM gate_sentence_run ORDER BY run_id DESC LIMIT 1
"""

CASES = """
SELECT case_name, sentences, view, model, merge, reduction, min_cluster_size AS mcs, min_samples AS ms, selection,
       structure, noise_passes AS passes, k, seed, top_removed, clusters, topics, input_sentences AS sentences_read,
       leaders, leaders_clustered, occurrences, occurrences_clustered, largest_cluster, gate_comments,
       comments_unclustered, opening_occurrences, opening_occurrences_clustered, eigengaps, seconds,
       sentence_run_id, substr(code_version, 1, 10) AS code, code_dirty, created_at
FROM cluster_case ORDER BY created_at
"""

CASE_TOPICS = """
SELECT topic, clusters, leaders, occurrences, terms
FROM cluster_case_topic WHERE case_name = ? ORDER BY topic
"""

CASE_CLUSTERS = """
SELECT cluster, kind, pass, leaders, variants, occurrences, tightness, law, evid, gap, alt, terms, central
FROM cluster_case_cluster WHERE case_name = ? AND topic = ? ORDER BY occurrences DESC, cluster
"""

# A cluster's leaders, or a case's noise (cluster 0): each with the sentences it
# absorbed and how often it and they occur in the gate set.
_LEADER_ROWS = """
FROM cluster_case_member m
JOIN gate_sentence s ON s.text_key = m.leader_key
JOIN (SELECT l.leader_key, count(*) - 1 AS variants, sum(g.occurrences) AS occurrences,
             sum(g.comments) AS comments
      FROM cluster_case_leader l JOIN gate_sentence g ON g.text_key = l.text_key
      WHERE l.case_name = ? GROUP BY l.leader_key) v ON v.leader_key = m.leader_key
WHERE m.case_name = ? AND m.cluster = ?
"""

CLUSTER_SENTENCE_COUNT = "SELECT count(DISTINCT m.leader_key) AS n " + _LEADER_ROWS

CLUSTER_SENTENCES = ("SELECT DISTINCT m.leader_key, s.text, v.variants, v.occurrences, v.comments " + _LEADER_ROWS
                     + " ORDER BY v.occurrences DESC, s.text LIMIT ? OFFSET ?")

CLUSTER_COMMENTS = """
SELECT DISTINCT o.comment_id
FROM cluster_case_member m
JOIN cluster_case_leader l ON l.case_name = m.case_name AND l.leader_key = m.leader_key
JOIN gate_sentence_occurrence o ON o.text_key = l.text_key
WHERE m.case_name = ? AND m.cluster = ?
ORDER BY o.comment_id
"""

# The comments that hold one leader's sentence or a near-copy joined to it.
LEADER_COMMENTS = """
SELECT DISTINCT o.comment_id
FROM cluster_case_leader l JOIN gate_sentence_occurrence o ON o.text_key = l.text_key
WHERE l.case_name = ? AND l.leader_key = ?
ORDER BY o.comment_id
"""

CHOICES = "SELECT model, case_name, note, chosen_at FROM cluster_case_choice ORDER BY model"

CONCERN_MAP = "SELECT case_name, note, decided_at FROM cluster_concern_map"

# The vectors of each model in its most complete view (the primary key's index covers
# it; no vector is read).
VECTORS = ("SELECT model, max(n) AS n FROM (SELECT model, instruction, count(*) AS n FROM sentence_embedding"
           " GROUP BY model, instruction) GROUP BY model ORDER BY model")

VECTORS_BY_VIEW = ("SELECT model, instruction, count(*) AS n FROM sentence_embedding"
                   " GROUP BY model, instruction ORDER BY model, instruction")

# The gate-opening sentences of each gate kind (a sentence of two kinds counts in both).
OPENING_KINDS = ("SELECT sum(law) AS LAW, sum(evid) AS EVID, sum(gap) AS GAP, sum(alt) AS ALT, count(*) AS n"
                 " FROM gate_sentence_occurrence WHERE opens = 1")

# The comments that hold a sentence of each cluster of one case.
_CASE_COMMENTS = """
FROM cluster_case_member m
JOIN cluster_case_leader l ON l.case_name = m.case_name AND l.leader_key = m.leader_key
JOIN gate_sentence_occurrence o ON o.text_key = l.text_key
WHERE m.case_name = ? AND m.cluster > 0
"""

CLUSTER_REACH = ("SELECT m.cluster, count(DISTINCT o.comment_id) AS comments" + _CASE_COMMENTS
                 + " GROUP BY m.cluster")

TOPIC_REACH = ("SELECT c.topic, count(DISTINCT o.comment_id) AS comments" + _CASE_COMMENTS.replace(
    "JOIN gate_sentence_occurrence", "JOIN cluster_case_cluster c ON c.case_name = m.case_name"
    " AND c.cluster = m.cluster\nJOIN gate_sentence_occurrence") + " GROUP BY c.topic")

# The comments by the number of clusters that hold one of their sentences.
COMMENT_SPREAD = ("SELECT clusters, count(*) AS comments FROM (SELECT o.comment_id, count(DISTINCT m.cluster)"
                  " AS clusters" + _CASE_COMMENTS + " GROUP BY o.comment_id) GROUP BY clusters ORDER BY clusters")
