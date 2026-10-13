-- schema/roadless.sql: the DDL of data/roadless.sqlite, the one file the analysis
-- lives in. Written for SQLite from the rtca roadless schema at the tag
-- reproduction-source (db/project_template/*.sql and the roadless migrations in
-- db/migrations_pending/), for the tables the nine steps write and the views they
-- read, and nothing else. Each table names its rtca source.
--
-- The translations, the same for every table:
--   serial, bigserial, identity   INTEGER PRIMARY KEY
--   timestamptz, timestamp        TEXT, ISO-8601, DEFAULT CURRENT_TIMESTAMP
--   boolean                       INTEGER 0 or 1
--   jsonb, text[], varchar[]      TEXT holding JSON, read and written with json
--   numeric, real, float          REAL
--   smallint, bigint, varchar(n)  INTEGER, TEXT
--   uuid                          TEXT
--   GIN and trigram indexes       dropped; the plain index on the value column stays
--   CHECKs over arrays            kept where SQLite's json1 can express them without a
--                                 subquery (which a CHECK may not hold); the rest are
--                                 enforced by the Python that writes the rows and by
--                                 its tests, named beside each
--   {analysis}.t, {src}.t         t (one file, one schema)
--
-- Functions the views and the steps call (regexp, regexp_count, md5,
-- authority_family_key) are registered on the connection by shared/db.py.
-- comment_facts is not here: `make facts` builds it with CREATE TABLE AS.

-- ===========================================================================
-- 1. The corpus (plan 3.1; new). One row per record of the bulk download,
--    blanks and withdrawn rows kept and flagged; one row per attachment
--    rendition. v_source_comments is every step's view of the text
--    (rtca 01_adapter_view.sql, adapter_view_received_date.sql) and excludes
--    the records with no text.
-- ===========================================================================

CREATE TABLE comment (
    comment_id        TEXT    PRIMARY KEY,
    comment_text      TEXT    NOT NULL,         -- '' for a blank or withdrawn record
    posted_date       TEXT,                     -- as the export gives it, e.g. 2026-08-20T04:00Z
    received_date     TEXT,
    withdrawn         INTEGER NOT NULL DEFAULT 0 CHECK (withdrawn IN (0, 1)),
    withdrawn_reason  TEXT,
    title             TEXT,
    tracking_number   TEXT,
    government_agency TEXT
);

CREATE TABLE attachment_file (
    comment_id TEXT    NOT NULL REFERENCES comment (comment_id),
    ordinal    INTEGER NOT NULL,               -- attachment_<n> in the URL
    format     TEXT    NOT NULL,               -- the extension: pdf, docx, jpg, ...
    url        TEXT    NOT NULL,
    PRIMARY KEY (comment_id, ordinal, format)
);

CREATE VIEW v_source_comments AS
SELECT comment_id,
       comment_text,
       posted_date,
       length(comment_text) AS comment_length,
       received_date
FROM comment
WHERE comment_text <> '';

-- ===========================================================================
-- 2. Copies (rtca 02_dedup.sql)
-- ===========================================================================

CREATE TABLE comment_dedup (
    comment_id             TEXT PRIMARY KEY,
    content_hash           TEXT,
    content_hash_md5       TEXT,
    is_original            INTEGER DEFAULT 1 CHECK (is_original IN (0, 1)),
    original_comment_id    TEXT REFERENCES comment_dedup (comment_id),
    duplicate_group_size   INTEGER DEFAULT 1,
    hash_updated_at        TEXT,
    middle_content_hash    TEXT,
    is_middle_original     INTEGER CHECK (is_middle_original IN (0, 1)),
    middle_original_id     TEXT,
    middle_dup_group_size  INTEGER DEFAULT 1,
    middle_hash_updated_at TEXT,
    CONSTRAINT chk_deduplication_consistency CHECK (
        (is_original = 1 AND original_comment_id IS NULL) OR
        (is_original = 0 AND original_comment_id IS NOT NULL)
    )
);

CREATE INDEX idx_comment_dedup_content_hash ON comment_dedup (content_hash);
CREATE INDEX idx_comment_dedup_content_hash_md5 ON comment_dedup (content_hash_md5);
CREATE INDEX idx_comment_dedup_is_original ON comment_dedup (is_original) WHERE is_original = 1;
CREATE INDEX idx_comment_dedup_original_comment ON comment_dedup (original_comment_id);
CREATE INDEX idx_comment_dedup_duplicate_groups ON comment_dedup (duplicate_group_size) WHERE duplicate_group_size > 1;
CREATE INDEX idx_comment_dedup_middle_hash ON comment_dedup (middle_content_hash);
CREATE INDEX idx_comment_dedup_middle_original ON comment_dedup (middle_original_id);

CREATE VIEW v_unique_comments AS
SELECT sc.comment_id, sc.comment_text, sc.posted_date, sc.comment_length,
       d.content_hash, d.content_hash_md5, d.duplicate_group_size
FROM v_source_comments sc
JOIN comment_dedup d ON sc.comment_id = d.comment_id
WHERE d.is_original = 1;

CREATE VIEW v_truly_unique_comments AS
SELECT sc.comment_id, sc.comment_text, sc.posted_date, sc.comment_length,
       d.content_hash,
       d.duplicate_group_size AS full_text_group_size,
       d.middle_content_hash,
       d.middle_dup_group_size
FROM v_source_comments sc
JOIN comment_dedup d ON sc.comment_id = d.comment_id
WHERE d.is_original = 1
  AND (d.is_middle_original = 1 OR d.is_middle_original IS NULL);

-- ===========================================================================
-- 3. Long n-grams (rtca 09_ngram_tables.sql, roadless_long_ngram_offsets.sql)
-- ===========================================================================

CREATE TABLE long_ngrams (
    ngram_id    INTEGER PRIMARY KEY,
    ngram_hash  TEXT    NOT NULL UNIQUE,
    ngram_text  TEXT    NOT NULL,
    n           INTEGER NOT NULL CHECK (n BETWEEN 6 AND 8),
    word_count  INTEGER NOT NULL,
    first_words TEXT,
    last_words  TEXT,
    created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_long_ngrams_hash ON long_ngrams (ngram_hash);
CREATE INDEX idx_long_ngrams_n ON long_ngrams (n);
CREATE INDEX idx_long_ngrams_first_words ON long_ngrams (first_words);
CREATE INDEX idx_long_ngrams_last_words ON long_ngrams (last_words);

CREATE TABLE comment_long_ngrams (
    comment_id        TEXT    NOT NULL,
    ngram_id          INTEGER NOT NULL REFERENCES long_ngrams (ngram_id),
    position          INTEGER NOT NULL,
    sentence_position INTEGER,
    char_start        INTEGER,
    char_end          INTEGER,
    PRIMARY KEY (comment_id, ngram_id, position)
);

CREATE INDEX idx_comment_long_ngrams_comment ON comment_long_ngrams (comment_id);
CREATE INDEX idx_comment_long_ngrams_ngram ON comment_long_ngrams (ngram_id);

CREATE TABLE long_ngram_stats (
    ngram_id              INTEGER PRIMARY KEY REFERENCES long_ngrams (ngram_id),
    document_frequency    INTEGER DEFAULT 0,
    comment_frequency     INTEGER NOT NULL DEFAULT 0,
    total_frequency       INTEGER DEFAULT 0,
    avg_position          REAL,
    std_position          REAL,
    is_template_candidate INTEGER DEFAULT 0 CHECK (is_template_candidate IN (0, 1)),
    template_confidence   REAL,
    first_seen            TEXT,
    last_seen             TEXT,
    updated_at            TEXT    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE template_blocks (
    block_id           INTEGER PRIMARY KEY,
    block_hash         TEXT    NOT NULL UNIQUE,
    ngram_sequence     TEXT,                    -- JSON array of n-gram hashes
    total_words        INTEGER,
    block_length       INTEGER,
    document_frequency INTEGER DEFAULT 0,
    created_at         TEXT    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_template_blocks_hash ON template_blocks (block_hash);
CREATE INDEX idx_template_blocks_freq ON template_blocks (document_frequency);

CREATE TABLE comment_templates (
    comment_id     TEXT    NOT NULL,
    block_id       INTEGER NOT NULL REFERENCES template_blocks (block_id),
    start_position INTEGER NOT NULL,
    end_position   INTEGER NOT NULL,
    coverage_ratio REAL,
    PRIMARY KEY (comment_id, block_id, start_position)
);

CREATE INDEX idx_comment_templates_comment ON comment_templates (comment_id);
CREATE INDEX idx_comment_templates_block ON comment_templates (block_id);
CREATE INDEX idx_comment_templates_coverage ON comment_templates (coverage_ratio);

CREATE TABLE long_ngram_processing_log (
    log_id             INTEGER PRIMARY KEY,
    batch_id           TEXT,
    comments_processed INTEGER,
    ngrams_extracted   INTEGER,
    templates_found    INTEGER,
    start_time         TEXT,
    end_time           TEXT,
    status             TEXT,
    error_message      TEXT,
    created_at         TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================================================
-- 4. Near-duplicate groups (rtca 10_duplicate_detection.sql)
-- ===========================================================================

CREATE TABLE duplicate_groups (
    group_id   INTEGER PRIMARY KEY,
    group_hash TEXT    NOT NULL UNIQUE,
    group_size INTEGER NOT NULL,
    created_at TEXT    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE duplicate_group_members (
    group_id          INTEGER NOT NULL REFERENCES duplicate_groups (group_id) ON DELETE CASCADE,
    comment_id        TEXT    NOT NULL,
    is_representative INTEGER DEFAULT 0 CHECK (is_representative IN (0, 1)),
    PRIMARY KEY (group_id, comment_id)
);

CREATE INDEX idx_duplicate_group_members_comment ON duplicate_group_members (comment_id);
CREATE INDEX idx_duplicate_group_members_representative ON duplicate_group_members (is_representative) WHERE is_representative = 1;

CREATE TABLE duplicate_detection_runs (
    run_id                  INTEGER PRIMARY KEY,
    run_timestamp           TEXT DEFAULT CURRENT_TIMESTAMP,
    detection_method        TEXT,
    min_shared_ngrams       INTEGER,
    similarity_threshold    REAL,
    total_comments_analyzed INTEGER,
    total_pairs_found       INTEGER,
    exact_duplicates        INTEGER,
    near_duplicates         INTEGER,
    form_letters            INTEGER,
    campaigns               INTEGER,
    execution_time_seconds  REAL,
    parameters              TEXT                 -- JSON
);

-- ===========================================================================
-- 5. Named entities (rtca 11_linguistic_patterns.sql; the noun, verb and SVO
--    tables are not here, plan 5.2 edit 3)
-- ===========================================================================

CREATE TABLE named_entities (
    entity_id   INTEGER PRIMARY KEY,
    comment_id  TEXT NOT NULL,
    entity_text TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    char_start  INTEGER,
    char_end    INTEGER,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_named_entities_comment_id ON named_entities (comment_id);
CREATE INDEX idx_named_entities_type ON named_entities (entity_type);
CREATE INDEX idx_named_entities_text ON named_entities (entity_text);

-- ===========================================================================
-- 6. The classification profile and the stance (rtca 12_profile_tables.sql,
--    13_classification.sql, roadless_classification_run_items.sql). The rows
--    of topics, prompts and sentiment come from seeds/ at make schema.
-- ===========================================================================

CREATE TABLE topics (
    topic_id         INTEGER PRIMARY KEY,
    topic_name       TEXT    NOT NULL UNIQUE,
    description      TEXT,
    key_phrases      TEXT,                       -- JSON array
    typical_position TEXT,
    category         TEXT,
    created_date     TEXT    DEFAULT CURRENT_TIMESTAMP,
    is_active        INTEGER DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE prompts (
    prompt_id            INTEGER PRIMARY KEY,
    prompt_kind          TEXT    NOT NULL CHECK (
                             prompt_kind IN ('sentiment_topic', 'topic_discovery', 'topic_consolidation')
                             OR prompt_kind LIKE 'dimension:%'),
    prompt_name          TEXT    NOT NULL,
    system_prompt        TEXT    NOT NULL,
    user_prompt_template TEXT    NOT NULL,
    model_name           TEXT    NOT NULL,
    model_parameters     TEXT    NOT NULL DEFAULT '{}',   -- JSON
    version              INTEGER NOT NULL DEFAULT 1,
    is_active            INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
    created_at           TEXT    DEFAULT CURRENT_TIMESTAMP,
    notes                TEXT
);

CREATE UNIQUE INDEX idx_prompts_one_active_per_kind ON prompts (prompt_kind) WHERE is_active = 1;

CREATE TABLE sentiment (
    sentiment_id  INTEGER PRIMARY KEY,
    sentiment     TEXT NOT NULL,
    meaning       TEXT,
    display_label TEXT
);

INSERT INTO sentiment (sentiment_id, sentiment) VALUES (1, 'SUPPORT'), (2, 'OPPOSE'), (3, 'NEUTRAL');

CREATE TABLE classification_runs (
    run_timestamp TEXT    PRIMARY KEY,
    prompt_id     INTEGER NOT NULL REFERENCES prompts (prompt_id),
    model_name    TEXT    NOT NULL,
    comment_count INTEGER NOT NULL,
    created_at    TEXT    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE comment_classification (
    classification_id  INTEGER PRIMARY KEY,
    comment_id         TEXT    NOT NULL,
    sentiment_id       INTEGER NOT NULL REFERENCES sentiment (sentiment_id),
    sentiment_strength TEXT    NOT NULL CHECK (sentiment_strength IN ('HIGH', 'MEDIUM', 'LOW')),
    processed_date     TEXT    DEFAULT CURRENT_TIMESTAMP,
    batch_id           TEXT,
    model_version      TEXT,
    custom_id          TEXT,
    processing_time_ms INTEGER,
    confidence_score   REAL    CHECK (confidence_score >= 0.00 AND confidence_score <= 1.00),
    created_by         TEXT,
    updated_date       TEXT,
    updated_by         TEXT,
    is_active          INTEGER DEFAULT 1 CHECK (is_active IN (0, 1)),
    notes              TEXT,
    UNIQUE (comment_id, batch_id)
);

CREATE INDEX idx_comment_classification_active ON comment_classification (is_active);
CREATE INDEX idx_comment_classification_batch ON comment_classification (batch_id);
CREATE INDEX idx_comment_classification_comment ON comment_classification (comment_id);
CREATE INDEX idx_comment_classification_composite ON comment_classification (comment_id, classification_id, sentiment_id) WHERE is_active = 1;
CREATE INDEX idx_comment_classification_custom_id ON comment_classification (custom_id);
CREATE INDEX idx_comment_classification_model ON comment_classification (model_version);
CREATE INDEX idx_comment_classification_processed_date ON comment_classification (processed_date);
CREATE INDEX idx_comment_classification_sentiment_active ON comment_classification (sentiment_id, is_active, classification_id) WHERE is_active = 1;
CREATE INDEX idx_comment_classification_strength ON comment_classification (sentiment_strength);
CREATE INDEX idx_classification_batch_active ON comment_classification (batch_id, is_active);
CREATE INDEX idx_classification_sentiment_active ON comment_classification (sentiment_id, is_active);

CREATE TABLE classification_topics (
    classification_topic_id INTEGER PRIMARY KEY,
    classification_id       INTEGER NOT NULL REFERENCES comment_classification (classification_id) ON DELETE CASCADE,
    topic_id                INTEGER NOT NULL REFERENCES topics (topic_id),
    confidence              REAL    NOT NULL CHECK (confidence >= 0.00 AND confidence <= 1.00),
    supporting_phrases      TEXT    NOT NULL,    -- JSON array
    phrase_count            INTEGER GENERATED ALWAYS AS (json_array_length(supporting_phrases)) STORED,
    rank_order              INTEGER,
    created_date            TEXT    DEFAULT CURRENT_TIMESTAMP,
    created_by              TEXT,
    updated_date            TEXT,
    updated_by              TEXT,
    is_active               INTEGER DEFAULT 1 CHECK (is_active IN (0, 1)),
    notes                   TEXT,
    UNIQUE (classification_id, topic_id),
    CONSTRAINT chk_phrase_count CHECK (json_array_length(supporting_phrases) >= 1)
);

CREATE INDEX idx_classification_topics_active ON classification_topics (is_active);
CREATE INDEX idx_classification_topics_classification ON classification_topics (classification_id);
CREATE INDEX idx_classification_topics_confidence ON classification_topics (confidence);
CREATE INDEX idx_classification_topics_phrase_count ON classification_topics (phrase_count);
CREATE INDEX idx_classification_topics_rank ON classification_topics (rank_order);
CREATE INDEX idx_classification_topics_topic ON classification_topics (topic_id);
CREATE INDEX idx_topics_classification_confidence ON classification_topics (classification_id, confidence DESC);

CREATE TABLE classification_run_items (
    run_id            TEXT    NOT NULL,
    group_id          INTEGER NOT NULL,
    attempt           INTEGER NOT NULL,
    comment_id        TEXT    NOT NULL,
    status            TEXT    NOT NULL CHECK (status IN ('received', 'loaded', 'error')),
    error_kind        TEXT    CHECK (error_kind IN ('transport', 'truncated', 'unparseable',
                                                    'unknown_topic', 'invalid_sentiment')),
    error_detail      TEXT,
    finish_reason     TEXT,
    prompt_tokens     INTEGER,
    cached_tokens     INTEGER,
    completion_tokens INTEGER,
    cost              REAL,
    seconds           REAL    NOT NULL,
    response          TEXT,                      -- JSON
    received_at       TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    loaded_at         TEXT,
    classification_id INTEGER,
    PRIMARY KEY (run_id, group_id, attempt),
    CHECK ((status = 'error') = (error_kind IS NOT NULL))
);

CREATE INDEX classification_run_items_status_idx ON classification_run_items (run_id, status);

-- ===========================================================================
-- 7. Entity tagging (rtca 23_entity_tagging.sql, roadless_dynamic_views.sql).
--    The three reference lists and the two seed CSVs are loaded by
--    scripts/entity_tagging/load_references.py in make tag.
-- ===========================================================================

CREATE TABLE forests (
    id   INTEGER PRIMARY KEY,
    name TEXT    NOT NULL UNIQUE
);

CREATE TABLE roadless_areas (
    id         INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL,
    forest     TEXT    NOT NULL,
    state      TEXT,
    state_name TEXT,
    acres      REAL,
    UNIQUE (name, forest)
);

CREATE TABLE species (
    id                  INTEGER PRIMARY KEY,
    primary_common_name TEXT    NOT NULL,
    scientific_name     TEXT    NOT NULL,
    usesa_code          TEXT,
    rounded_g_rank      TEXT,
    area_count          INTEGER,
    state_count         INTEGER,
    states              TEXT
);

CREATE TABLE legal_authority (
    id         INTEGER PRIMARY KEY,
    seed_id    TEXT,                             -- from the seed CSV; NULL on discovered rows
    type       TEXT,
    display    TEXT NOT NULL,
    citation   TEXT,
    case_name  TEXT,
    match_keys TEXT,
    cite_role  TEXT,
    status     TEXT,
    summary    TEXT
);

CREATE UNIQUE INDEX uq_legal_authority_discovered ON legal_authority (citation) WHERE seed_id IS NULL;

CREATE TABLE cited_references (
    id           INTEGER PRIMARY KEY,
    seed_id      TEXT,
    type         TEXT,
    display      TEXT NOT NULL,
    citation_key TEXT,
    match_keys   TEXT,
    authors      TEXT,
    year         TEXT,
    title        TEXT,
    publisher    TEXT,
    url          TEXT,
    raw_text     TEXT
);

CREATE UNIQUE INDEX uq_cited_references_discovered ON cited_references (citation_key) WHERE seed_id IS NULL;

CREATE TABLE zipcodes (
    id      INTEGER PRIMARY KEY,
    zipcode TEXT NOT NULL UNIQUE
);

CREATE TABLE entity_scan_state (
    comment_id       TEXT    PRIMARY KEY REFERENCES comment (comment_id) ON DELETE CASCADE,
    is_tagged_strict INTEGER CHECK (is_tagged_strict IN (0, 1)),
    is_tagged_loose  INTEGER CHECK (is_tagged_loose IN (0, 1))
);

CREATE TABLE comment_forests (
    id           INTEGER PRIMARY KEY,
    comment_id   TEXT NOT NULL REFERENCES comment (comment_id) ON DELETE CASCADE,
    forest_name  TEXT NOT NULL,
    matched_text TEXT NOT NULL,
    mode         TEXT NOT NULL CHECK (mode IN ('strict', 'loose')),
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (comment_id, forest_name, mode, matched_text)
);
CREATE INDEX idx_comment_forests_value ON comment_forests (forest_name);
CREATE INDEX comment_forests_strict_value_comment_idx ON comment_forests (forest_name, comment_id) WHERE mode = 'strict';

CREATE TABLE comment_areas (
    id           INTEGER PRIMARY KEY,
    comment_id   TEXT NOT NULL REFERENCES comment (comment_id) ON DELETE CASCADE,
    area_name    TEXT NOT NULL,
    matched_text TEXT NOT NULL,
    mode         TEXT NOT NULL CHECK (mode IN ('strict', 'loose')),
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (comment_id, area_name, mode, matched_text)
);
CREATE INDEX idx_comment_areas_value ON comment_areas (area_name);
CREATE INDEX comment_areas_strict_value_comment_idx ON comment_areas (area_name, comment_id) WHERE mode = 'strict';

CREATE TABLE comment_species (
    id           INTEGER PRIMARY KEY,
    comment_id   TEXT NOT NULL REFERENCES comment (comment_id) ON DELETE CASCADE,
    species_name TEXT NOT NULL,
    matched_text TEXT NOT NULL,
    mode         TEXT NOT NULL CHECK (mode IN ('strict', 'loose')),
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (comment_id, species_name, mode, matched_text)
);
CREATE INDEX idx_comment_species_value ON comment_species (species_name);
CREATE INDEX comment_species_strict_value_comment_idx ON comment_species (species_name, comment_id) WHERE mode = 'strict';

-- family_key: NOT NULL, written on insert by run_pass.py through the registered
-- authority_family_key (plan 4.4).
CREATE TABLE comment_authorities (
    id           INTEGER PRIMARY KEY,
    comment_id   TEXT NOT NULL REFERENCES comment (comment_id) ON DELETE CASCADE,
    citation     TEXT NOT NULL,
    matched_text TEXT NOT NULL,
    mode         TEXT NOT NULL CHECK (mode IN ('strict', 'loose')),
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    family_key   TEXT NOT NULL,
    UNIQUE (comment_id, citation, mode, matched_text)
);
CREATE INDEX idx_comment_authorities_value ON comment_authorities (citation);
CREATE INDEX comment_authorities_strict_value_comment_idx ON comment_authorities (citation, comment_id) WHERE mode = 'strict';
CREATE INDEX comment_authorities_strict_family_comment_idx ON comment_authorities (family_key, comment_id) WHERE mode = 'strict';

CREATE TABLE comment_cited_references (
    id           INTEGER PRIMARY KEY,
    comment_id   TEXT NOT NULL REFERENCES comment (comment_id) ON DELETE CASCADE,
    citation_key TEXT NOT NULL,
    matched_text TEXT NOT NULL,
    mode         TEXT NOT NULL CHECK (mode IN ('strict', 'loose')),
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (comment_id, citation_key, mode, matched_text)
);
CREATE INDEX idx_comment_cited_references_value ON comment_cited_references (citation_key);
CREATE INDEX comment_cited_references_strict_value_comment_idx ON comment_cited_references (citation_key, comment_id) WHERE mode = 'strict';

CREATE TABLE comment_zipcodes (
    id           INTEGER PRIMARY KEY,
    comment_id   TEXT NOT NULL REFERENCES comment (comment_id) ON DELETE CASCADE,
    zipcode      TEXT NOT NULL,
    city         TEXT,
    state        TEXT,
    matched_text TEXT NOT NULL,
    mode         TEXT NOT NULL CHECK (mode IN ('strict', 'loose')),
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (comment_id, zipcode, mode, matched_text)
);
CREATE INDEX idx_comment_zipcodes_value ON comment_zipcodes (zipcode);
CREATE INDEX comment_zipcodes_strict_value_comment_idx ON comment_zipcodes (zipcode, comment_id) WHERE mode = 'strict';
CREATE INDEX comment_zipcodes_strict_state_comment_idx ON comment_zipcodes (state, comment_id) WHERE mode = 'strict' AND city IS NOT NULL;

-- One row per authority family; canonical when any legal_authority seed maps
-- into it. Built by the tag step from comment_authorities (rtca migration 0069).
CREATE TABLE authority_family (
    family_key TEXT    PRIMARY KEY,
    canonical  INTEGER NOT NULL CHECK (canonical IN (0, 1))
);

-- ===========================================================================
-- 8. Text families and the partition (rtca 25_text_families.sql,
--    24_comment_groups.sql, roadless_comment_group_analysis_comment_id.sql)
-- ===========================================================================

CREATE TABLE text_family (
    family_id           INTEGER PRIMARY KEY,
    exemplar_comment_id TEXT    NOT NULL,
    core_kind           TEXT    NOT NULL,
    n_texts             INTEGER NOT NULL,
    n_comments          INTEGER NOT NULL,
    is_campaign         INTEGER NOT NULL CHECK (is_campaign IN (0, 1)),
    family_text_min     INTEGER NOT NULL,
    params              TEXT    NOT NULL,         -- JSON
    built_at            TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT text_family_core_kind CHECK (core_kind IN ('exact', 'middle', 'near', 'contain')),
    CONSTRAINT text_family_size CHECK (n_comments >= n_texts AND n_texts >= 1)
);

CREATE TABLE text_family_ngram (
    family_id    INTEGER NOT NULL REFERENCES text_family (family_id) ON DELETE CASCADE,
    ngram_id     INTEGER NOT NULL,
    n_core_texts INTEGER NOT NULL,
    distinctive  INTEGER NOT NULL CHECK (distinctive IN (0, 1)),
    PRIMARY KEY (family_id, ngram_id)
);

CREATE INDEX text_family_ngram_ngram_idx ON text_family_ngram (ngram_id) WHERE distinctive = 1;

CREATE TABLE text_family_member (
    comment_id        TEXT    PRIMARY KEY,
    family_id         INTEGER NOT NULL REFERENCES text_family (family_id) ON DELETE CASCADE,
    joined_via        TEXT    NOT NULL,
    coverage          REAL,
    shared_chars      INTEGER,
    own_chars         INTEGER,
    own_tokens        INTEGER,
    own_in_margin     INTEGER CHECK (own_in_margin IN (0, 1)),
    has_own_text      INTEGER NOT NULL CHECK (has_own_text IN (0, 1)),
    own_sentence_keys TEXT,                       -- JSON array, NULL for a non-survivor
    CONSTRAINT text_family_member_via CHECK (joined_via IN ('core', 'attach'))
);

CREATE INDEX text_family_member_family_idx ON text_family_member (family_id);

CREATE TABLE text_family_sentence (
    family_id    INTEGER NOT NULL REFERENCES text_family (family_id) ON DELETE CASCADE,
    sentence_key TEXT    NOT NULL,
    n_comments   INTEGER NOT NULL,
    PRIMARY KEY (family_id, sentence_key)
);

CREATE TABLE text_family_span (
    comment_id TEXT    NOT NULL REFERENCES text_family_member (comment_id) ON DELETE CASCADE,
    char_start INTEGER NOT NULL,
    char_end   INTEGER NOT NULL,
    tier       INTEGER NOT NULL,
    PRIMARY KEY (comment_id, char_start),
    CONSTRAINT text_family_span_order CHECK (char_end > char_start),
    CONSTRAINT text_family_span_tier CHECK (tier IN (1, 2))
);

CREATE TABLE comment_group (
    group_id             INTEGER PRIMARY KEY,
    group_kind           TEXT    NOT NULL,
    group_key            TEXT    NOT NULL,
    canonical_comment_id TEXT    NOT NULL,
    size                 INTEGER NOT NULL,
    first_seen_at        TEXT    NOT NULL,
    built_at             TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    family_id            INTEGER,
    analysis_comment_id  TEXT,
    CONSTRAINT comment_group_kind_vocab
        CHECK (group_kind IN ('exact', 'middle', 'family', 'campaign', 'singleton')),
    CONSTRAINT comment_group_size_positive CHECK (size >= 1),
    CONSTRAINT comment_group_singleton_is_one CHECK (group_kind <> 'singleton' OR size = 1),
    CONSTRAINT comment_group_key_unique UNIQUE (group_kind, group_key),
    -- Both deferred: the group row precedes the members it points at.
    CONSTRAINT comment_group_canonical_is_member
        FOREIGN KEY (group_id, canonical_comment_id)
        REFERENCES comment_group_member (group_id, comment_id)
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT comment_group_analysis_is_member
        FOREIGN KEY (group_id, analysis_comment_id)
        REFERENCES comment_group_member (group_id, comment_id)
        DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE comment_group_member (
    comment_id   TEXT    PRIMARY KEY,
    group_id     INTEGER NOT NULL REFERENCES comment_group (group_id) ON DELETE CASCADE,
    has_own_text INTEGER NOT NULL CHECK (has_own_text IN (0, 1)),
    CONSTRAINT comment_group_member_group_comment UNIQUE (group_id, comment_id)
);

CREATE INDEX comment_group_member_group_idx ON comment_group_member (group_id);
CREATE INDEX comment_group_family_idx ON comment_group (family_id) WHERE family_id IS NOT NULL;
CREATE INDEX comment_group_analysis_comment_id_idx ON comment_group (analysis_comment_id);

CREATE VIEW v_comment_group_member AS
SELECT m.comment_id, m.group_id, g.group_kind, g.group_key, g.size,
       g.canonical_comment_id,
       (m.comment_id = g.canonical_comment_id) AS is_canonical,
       m.has_own_text
FROM comment_group_member m
JOIN comment_group g USING (group_id);

CREATE VIEW v_comment_representative AS
SELECT m.comment_id, g.canonical_comment_id AS rep_comment_id,
       g.group_id, g.group_kind, g.size
FROM comment_group_member m
JOIN comment_group g USING (group_id);

-- ===========================================================================
-- 9. Substance (rtca 22_substance_tables.sql with substance_score_provenance,
--    substance_scores_instrument_fields and substance_instrument_v3 folded in;
--    substance_screen.sql; substance_answerability.sql)
-- ===========================================================================

CREATE TABLE substance_floor (
    comment_id      TEXT    PRIMARY KEY,
    floored         INTEGER NOT NULL CHECK (floored IN (0, 1)),
    has_entity      INTEGER NOT NULL CHECK (has_entity IN (0, 1)),
    has_citation    INTEGER NOT NULL CHECK (has_citation IN (0, 1)),
    has_deficiency  INTEGER NOT NULL CHECK (has_deficiency IN (0, 1)),
    has_firstperson INTEGER NOT NULL CHECK (has_firstperson IN (0, 1)),
    comment_len     INTEGER,
    analyzed_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_substance_floor_floored ON substance_floor (floored);

CREATE TABLE substance_screen (
    comment_id   TEXT    PRIMARY KEY,
    screen_class TEXT    NOT NULL CHECK (screen_class IN ('A', 'B1', 'B2')),
    authority    INTEGER NOT NULL CHECK (authority IN (0, 1)),
    reference    INTEGER NOT NULL CHECK (reference IN (0, 1)),
    doc_cite     INTEGER NOT NULL CHECK (doc_cite IN (0, 1)),
    action_ref   INTEGER NOT NULL CHECK (action_ref IN (0, 1)),
    deficiency   INTEGER NOT NULL CHECK (deficiency IN (0, 1)),
    evid_ner     INTEGER NOT NULL CHECK (evid_ner IN (0, 1)),
    computed_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT substance_screen_class_derivation CHECK (
        screen_class = CASE
            WHEN authority = 1 OR reference = 1 OR doc_cite = 1
                 OR (deficiency = 1 AND action_ref = 1) THEN 'A'
            WHEN action_ref = 1 AND (deficiency = 1 OR evid_ner = 1) THEN 'B1'
            ELSE 'B2' END)
);
CREATE INDEX substance_screen_class_idx ON substance_screen (screen_class);

CREATE TABLE substance_scores (
    comment_id        TEXT    PRIMARY KEY,
    was_floored       INTEGER NOT NULL CHECK (was_floored IN (0, 1)),
    gate              INTEGER NOT NULL CHECK (gate IN (0, 1)),
    strength          INTEGER NOT NULL,
    strength_check    INTEGER NOT NULL,
    strength_reported INTEGER,
    gate_reported     INTEGER CHECK (gate_reported IN (0, 1)),
    band              TEXT    NOT NULL CHECK (band IN ('minimal', 'marginal', 'developed', 'strong')),
    place INTEGER CHECK (place BETWEEN 0 AND 3),
    stand INTEGER CHECK (stand BETWEEN 0 AND 3),
    doc   INTEGER CHECK (doc   BETWEEN 0 AND 3),
    gap   INTEGER CHECK (gap   BETWEEN 0 AND 3),
    evid  INTEGER CHECK (evid  BETWEEN 0 AND 3),
    ask   INTEGER CHECK (ask   BETWEEN 0 AND 3),
    alt   INTEGER CHECK (alt   BETWEEN 0 AND 3),
    law   INTEGER CHECK (law   BETWEEN 0 AND 3),
    gate_basis TEXT NOT NULL DEFAULT '[]',        -- JSON arrays
    moves      TEXT NOT NULL DEFAULT '[]',
    targets    TEXT NOT NULL DEFAULT '[]',
    topics     TEXT NOT NULL DEFAULT '[]',
    originality TEXT CHECK (originality IN ('verbatim_template', 'template_plus_original',
                                            'original', 'unknown')),
    harm_stated TEXT CHECK (harm_stated IN ('none', 'general', 'specific')),
    issue_count INTEGER,
    language    TEXT,
    attachments_referenced    INTEGER CHECK (attachments_referenced IN (0, 1)),
    data_offered              INTEGER CHECK (data_offered IN (0, 1)),
    mischaracterization       INTEGER CHECK (mischaracterization IN (0, 1)),
    off_topic_content         INTEGER CHECK (off_topic_content IN (0, 1)),
    incorporates_by_reference INTEGER CHECK (incorporates_by_reference IN (0, 1)),
    scored_by  TEXT,
    model      TEXT,
    tokens_in  INTEGER,
    tokens_out INTEGER,
    ms         INTEGER,
    rationale  TEXT,
    scored_via TEXT NOT NULL DEFAULT 'direct'
               CHECK (scored_via IN ('direct', 'exemplar', 'delta', 'inherited')),
    exemplar_id TEXT,
    instrument_version TEXT NOT NULL DEFAULT 'v1' CHECK (instrument_version IN ('v1', 'v2', 'v3')),
    scored_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT substance_scores_exemplar_presence CHECK (
        (scored_via IN ('inherited', 'delta')) = (exemplar_id IS NOT NULL))
);
CREATE INDEX idx_substance_scores_gate ON substance_scores (gate) WHERE gate = 1;
CREATE INDEX idx_substance_scores_band ON substance_scores (band);
CREATE INDEX idx_substance_scores_strength ON substance_scores (strength);
CREATE INDEX idx_substance_scores_survivor ON substance_scores (was_floored);
CREATE INDEX idx_substance_scores_via ON substance_scores (scored_via);
CREATE INDEX idx_substance_scores_instrument ON substance_scores (instrument_version);

CREATE TABLE substance_score_parts (
    comment_id TEXT NOT NULL,
    part       TEXT NOT NULL CHECK (part IN ('exemplar', 'delta')),
    place INTEGER CHECK (place BETWEEN 0 AND 3),
    stand INTEGER CHECK (stand BETWEEN 0 AND 3),
    doc   INTEGER CHECK (doc   BETWEEN 0 AND 3),
    gap   INTEGER CHECK (gap   BETWEEN 0 AND 3),
    evid  INTEGER CHECK (evid  BETWEEN 0 AND 3),
    ask   INTEGER CHECK (ask   BETWEEN 0 AND 3),
    alt   INTEGER CHECK (alt   BETWEEN 0 AND 3),
    law   INTEGER CHECK (law   BETWEEN 0 AND 3),
    strength INTEGER NOT NULL,
    gate     INTEGER NOT NULL CHECK (gate IN (0, 1)),
    band     TEXT    NOT NULL CHECK (band IN ('minimal', 'marginal', 'developed', 'strong')),
    model    TEXT,
    instrument_version TEXT NOT NULL CHECK (instrument_version IN ('v1', 'v2', 'v3')),
    rationale TEXT,
    record    TEXT NOT NULL,                     -- JSON, the finalized record verbatim
    scored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (comment_id, part)
);
CREATE INDEX idx_substance_score_parts_part ON substance_score_parts (part);

-- The scoring run's statistics, kept whole (rtca 22_substance_tables.sql).
CREATE TABLE substance_artifacts (
    kind      TEXT PRIMARY KEY,
    payload   TEXT NOT NULL,                     -- JSON
    loaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Every comment -> the comment whose floor or score row covers it, over the
-- two hash layers (rtca 22_substance_tables.sql; DISTINCT ON as row_number).
CREATE VIEW v_substance_representative AS
WITH RECURSIVE chain (comment_id, rep_id, hops) AS (
    SELECT d.comment_id, d.comment_id, 0
    FROM comment_dedup d
    UNION ALL
    SELECT c.comment_id, nxt.comment_id, c.hops + 1
    FROM chain c
    JOIN comment_dedup cur ON cur.comment_id = c.rep_id
    JOIN comment_dedup nxt
      ON (cur.is_original = 0
          AND nxt.content_hash = cur.content_hash AND nxt.is_original = 1)
      OR (cur.is_original = 1 AND cur.is_middle_original = 0
          AND nxt.middle_content_hash = cur.middle_content_hash
          AND nxt.is_middle_original = 1)
    WHERE c.hops < 6
      AND NOT EXISTS (SELECT 1 FROM substance_floor f WHERE f.comment_id = c.rep_id)
),
ranked AS (
    SELECT comment_id, rep_id, hops,
           row_number() OVER (PARTITION BY comment_id ORDER BY hops DESC) AS rn
    FROM chain
)
SELECT comment_id,
       rep_id AS rep_comment_id,
       hops,
       EXISTS (SELECT 1 FROM substance_floor f WHERE f.comment_id = rep_id) AS resolved
FROM ranked
WHERE rn = 1;

CREATE TABLE answerability_run (
    run_id             INTEGER PRIMARY KEY,
    rater              TEXT NOT NULL,
    evidence           TEXT NOT NULL CHECK (evidence IN ('text_only', 'deis')),
    deis_ref           TEXT,
    weights_version    TEXT NOT NULL,
    instrument_version TEXT NOT NULL,
    note               TEXT,
    created_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT answerability_run_deis_ref_required
        CHECK ((evidence = 'deis') = (deis_ref IS NOT NULL))
);

CREATE UNIQUE INDEX answerability_run_identity_idx
    ON answerability_run (rater, evidence, coalesce(deis_ref, ''), weights_version, instrument_version);

-- The array CHECKs of the rtca table that need a subquery (every code in the
-- nine, none in both sets) are enforced by answerability.rate and
-- tests/substance/test_answerability.py; the three a CHECK can hold are kept.
CREATE TABLE substance_answerability (
    run_id              INTEGER NOT NULL REFERENCES answerability_run (run_id) ON DELETE CASCADE,
    comment_id          TEXT    NOT NULL REFERENCES substance_scores (comment_id) ON DELETE CASCADE,
    a_level             TEXT    NOT NULL CHECK (a_level IN ('A0', 'A1', 'A2', 'A3')),
    gated               INTEGER NOT NULL CHECK (gated IN (0, 1)),
    limbs_reached       TEXT    NOT NULL,        -- JSON arrays
    answerability       REAL    NOT NULL,
    dismissals_defeated TEXT    NOT NULL,
    dismissals_open     TEXT    NOT NULL,
    mechanism           INTEGER NOT NULL CHECK (mechanism IN (0, 1)),
    mechanism_moves     TEXT,
    mechanism_targets   TEXT,
    cite_via            TEXT,
    PRIMARY KEY (run_id, comment_id),
    CONSTRAINT substance_answerability_codes_partitioned CHECK (
        json_array_length(dismissals_defeated) + json_array_length(dismissals_open) = 9),
    CONSTRAINT substance_answerability_ungated_defeats_nothing CHECK (
        gated = 1 OR json_array_length(dismissals_defeated) = 0),
    CONSTRAINT substance_answerability_level_derivation CHECK (
        a_level = CASE
            WHEN gated = 0 THEN 'A0'
            WHEN instr(dismissals_defeated, '"addressed_in_analysis"') > 0 THEN 'A1'
            WHEN instr(dismissals_defeated, '"no_cause_effect"') > 0 THEN 'A2'
            ELSE 'A3' END)
);
CREATE INDEX substance_answerability_comment_idx ON substance_answerability (comment_id);
CREATE INDEX substance_answerability_run_level_idx ON substance_answerability (run_id, a_level);

CREATE VIEW v_substance_answerability AS
SELECT a.run_id, r.rater, r.evidence, r.deis_ref,
       r.weights_version, r.instrument_version,
       a.comment_id, s.strength, s.band, s.gate, s.gate_basis,
       a.gated, a.a_level, a.limbs_reached, a.answerability,
       a.dismissals_defeated, a.dismissals_open,
       s.strength || a.a_level AS composite
FROM substance_answerability a
JOIN answerability_run r USING (run_id)
JOIN substance_scores s USING (comment_id);

-- ===========================================================================
-- 10. Attachments (rtca 28_attachment_text.sql, roadless_attachment_ocr.sql,
--     roadless_dynamic_views.sql, roadless_comment_organisation.sql)
-- ===========================================================================

CREATE TABLE comment_attachment_text (
    comment_id    TEXT    NOT NULL,
    attachment_id TEXT    NOT NULL,
    title         TEXT,
    formats       TEXT    NOT NULL,              -- JSON array
    pdf_text      TEXT,
    pdf_chars     INTEGER,
    pdf_pages     INTEGER,
    docx_text     TEXT,
    docx_chars    INTEGER,
    rtf_text      TEXT,
    rtf_chars     INTEGER,
    txt_text      TEXT,
    txt_chars     INTEGER,
    extracted_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pdf_ocr       INTEGER NOT NULL DEFAULT 0 CHECK (pdf_ocr IN (0, 1)),
    PRIMARY KEY (comment_id, attachment_id)
);

-- Per comment with a text attachment: its own text, and its own text followed
-- by each attachment's longest rendition (the LATERAL of the rtca view as a
-- union ranked by row_number; ties by format name, as ORDER BY chars DESC, fmt).
CREATE VIEW v_merged_comments AS
WITH rendition AS (
    SELECT comment_id, attachment_id, title, 'pdf' AS fmt, pdf_text AS body, pdf_chars AS chars
    FROM comment_attachment_text WHERE pdf_text IS NOT NULL
    UNION ALL
    SELECT comment_id, attachment_id, title, 'docx', docx_text, docx_chars
    FROM comment_attachment_text WHERE docx_text IS NOT NULL
    UNION ALL
    SELECT comment_id, attachment_id, title, 'rtf', rtf_text, rtf_chars
    FROM comment_attachment_text WHERE rtf_text IS NOT NULL
    UNION ALL
    SELECT comment_id, attachment_id, title, 'txt', txt_text, txt_chars
    FROM comment_attachment_text WHERE txt_text IS NOT NULL
),
best AS (
    SELECT comment_id, attachment_id, title, fmt, body, chars
    FROM (SELECT r.*, row_number() OVER (PARTITION BY comment_id, attachment_id
                                         ORDER BY chars DESC, fmt) AS rn
          FROM rendition r)
    WHERE rn = 1 AND chars >= 200
),
piece AS (
    SELECT comment_id, attachment_id,
           char(10) || char(10) || '[Attachment: ' || coalesce(title, attachment_id) || ']' || char(10) || body AS text
    FROM best
    ORDER BY comment_id, attachment_id
),
image_only AS (
    SELECT comment_id, count(*) AS n
    FROM comment_attachment_text
    WHERE pdf_chars = 0
      AND docx_text IS NULL AND rtf_text IS NULL AND txt_text IS NULL
    GROUP BY comment_id
)
SELECT c.comment_id,
       c.comment_text                           AS own_text,
       c.comment_length                         AS own_length,
       c.comment_text || group_concat(p.text, '') AS merged_text,
       c.comment_length + sum(length(p.text))   AS merged_length,
       count(*)                                 AS n_documents,
       coalesce(max(i.n), 0)                    AS n_image_only
FROM piece p
JOIN v_source_comments c USING (comment_id)
LEFT JOIN image_only i USING (comment_id)
GROUP BY c.comment_id, c.comment_text, c.comment_length;

CREATE TABLE comment_attachment_kind (
    comment_id    TEXT NOT NULL,
    attachment_id TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('own_letter', 'enclosed_submissions',
                                                'supporting_material', 'image')),
    PRIMARY KEY (comment_id, attachment_id)
);

CREATE TABLE comment_attachment_count (
    comment_id   TEXT    PRIMARY KEY,
    n_files      INTEGER NOT NULL CHECK (n_files >= 1),
    counts_as    INTEGER NOT NULL CHECK (counts_as >= 1),
    basis        TEXT    NOT NULL CHECK (basis IN ('one', 'measured', 'declared')),
    measured     INTEGER,
    declared     INTEGER,
    organisation TEXT,
    n_signature  INTEGER,
    n_form       INTEGER,
    n_unique     INTEGER,
    n_unread     INTEGER
);

CREATE TABLE comment_organisation (
    comment_id          TEXT    PRIMARY KEY,
    sender_kind         TEXT    NOT NULL CHECK (sender_kind IN ('organisation', 'government', 'individual', 'unclear')),
    organisation        TEXT,
    signatories         TEXT    NOT NULL DEFAULT '[]',   -- JSON arrays
    signer_count_stated INTEGER,
    stance              TEXT    NOT NULL CHECK (stance IN ('oppose', 'support', 'mixed', 'unclear')),
    stance_quote        TEXT,
    source              TEXT    NOT NULL CHECK (source IN ('attachment', 'comment_text')),
    flags               TEXT    NOT NULL DEFAULT '[]',
    instrument_version  TEXT    NOT NULL,
    model               TEXT    NOT NULL,
    read_at             TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX comment_organisation_organisation_idx ON comment_organisation (organisation) WHERE organisation IS NOT NULL;
CREATE INDEX comment_organisation_kind_stance_idx ON comment_organisation (sender_kind, stance);

-- ===========================================================================
-- 11. Campaign organisations (rtca roadless_family_organisation.sql)
-- ===========================================================================

CREATE TABLE family_organisation (
    family_id    INTEGER PRIMARY KEY,
    organisation TEXT    NOT NULL,
    basis        TEXT    NOT NULL CHECK (basis IN ('enclosed', 'cover', 'letter', 'action_page')),
    evidence     TEXT    NOT NULL,
    n_records    INTEGER,
    n_bundles    INTEGER,
    matched_at   TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================================================
-- 12. The vocabulary (rtca roadless_vocabulary.sql); rows from seeds/vocabulary.csv
-- ===========================================================================

CREATE TABLE vocabulary (
    kind    TEXT    NOT NULL,
    code    TEXT    NOT NULL,
    label   TEXT    NOT NULL,
    meaning TEXT    NOT NULL,
    ordinal INTEGER NOT NULL,
    lo      INTEGER,
    hi      INTEGER,
    PRIMARY KEY (kind, code)
);
