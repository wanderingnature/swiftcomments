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
            ("survivors", "SELECT count(*) FROM substance_floor WHERE floored = 1"),
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
        "target": "score",
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
        "target": "score-rules",
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
]

TABLES = ("SELECT type, name FROM sqlite_master WHERE type IN ('table', 'view')"
          " AND name NOT LIKE 'sqlite_%' ORDER BY type, name")
