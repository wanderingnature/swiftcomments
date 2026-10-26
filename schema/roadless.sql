-- schema/roadless.sql: the DDL of data/roadless.sqlite, the one file the analysis
-- lives in: the tables the nine steps write and the views they read, and
-- nothing else.
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
-- 1. The corpus. One row per record of the bulk download,
--    blanks and withdrawn rows kept and flagged; one row per attachment
--    rendition. v_source_comments is every step's view of the text and
--    excludes the records with no text.
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
-- 2. Copies
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
-- 3. Long n-grams
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
-- 4. Near-duplicate groups
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
-- 5. Named entities
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
-- 6. The classification profile and the stance. The rows
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
    created_at    TEXT    DEFAULT CURRENT_TIMESTAMP,
    refused_in    TEXT                            -- the run whose refused groups this run is confined to
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
                                                    'unknown_topic', 'invalid_sentiment',
                                                    'refused')),   -- the provider's content inspection
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
-- 7. Entity tagging.
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
-- authority_family_key.
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
-- into it. Built by the tag step from comment_authorities.
CREATE TABLE authority_family (
    family_key TEXT    PRIMARY KEY,
    canonical  INTEGER NOT NULL CHECK (canonical IN (0, 1))
);

-- ===========================================================================
-- 8. Text families and the partition
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
-- 9. Substance: the floor, the screen, the scores and the answerability
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
    prong_impacts      INTEGER NOT NULL DEFAULT 0 CHECK (prong_impacts IN (0, 1)),
    prong_significance INTEGER NOT NULL DEFAULT 0 CHECK (prong_significance IN (0, 1)),
    prong_alternatives INTEGER NOT NULL DEFAULT 0 CHECK (prong_alternatives IN (0, 1)),
    prong_compliance   INTEGER NOT NULL DEFAULT 0 CHECK (prong_compliance IN (0, 1)),
    prong_impacts_basis      TEXT NOT NULL DEFAULT '[]',
    prong_significance_basis TEXT NOT NULL DEFAULT '[]',
    prong_alternatives_basis TEXT NOT NULL DEFAULT '[]',
    prong_compliance_basis   TEXT NOT NULL DEFAULT '[]',
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

-- The scoring run's statistics, kept whole.
CREATE TABLE substance_artifacts (
    kind      TEXT PRIMARY KEY,
    payload   TEXT NOT NULL,                     -- JSON
    loaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Every comment -> the comment whose floor or score row covers it, over the
-- two hash layers.
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

-- The array checks that need a subquery (every code in the
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
-- 9b. The model-free reading (scripts/model_free/, rule set 3). The five mf_*
--     tables, in the one file so the console, the extracts and the jump see
--     them. A unit row is a sentence of the comment (unit_id the comment row's rowid
--     times 100,000 plus its place from one; start_char and end_char its span
--     in the stored text) or the whole comment (unit_id the negative of its
--     first sentence's), as hybrid mode scores both (docs/model-free-scoring.md).
-- ===========================================================================

CREATE TABLE mf_score_run (
    run_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ruleset_version     TEXT NOT NULL,
    started_at          TEXT NOT NULL,
    finished_at         TEXT,
    units_scored        INTEGER NOT NULL DEFAULT 0,
    comments_scored     INTEGER NOT NULL DEFAULT 0,
    counts_json         TEXT NOT NULL DEFAULT '{}',
    checks_json         TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE mf_sentence_score (
    ruleset_version  TEXT NOT NULL,
    unit_id          INTEGER NOT NULL,
    run_id           INTEGER NOT NULL,
    comment_id       TEXT NOT NULL,
    start_char       INTEGER NOT NULL,
    end_char         INTEGER NOT NULL,
    text_key         TEXT NOT NULL,
    place INTEGER NOT NULL, stand INTEGER NOT NULL, doc INTEGER NOT NULL, gap INTEGER NOT NULL,
    evid INTEGER NOT NULL, ask INTEGER NOT NULL, alt INTEGER NOT NULL, law INTEGER NOT NULL,
    strength         INTEGER NOT NULL,
    gate             INTEGER NOT NULL,
    gate_basis       TEXT NOT NULL,
    band             TEXT NOT NULL,
    moves            TEXT NOT NULL,
    targets          TEXT NOT NULL,
    evid_applied     INTEGER NOT NULL,
    ask_names        INTEGER NOT NULL,
    alt_distinct     INTEGER NOT NULL,
    stand_this_place INTEGER NOT NULL,
    is_record_text   INTEGER NOT NULL,
    anchors          TEXT NOT NULL,
    PRIMARY KEY (ruleset_version, unit_id)
);
CREATE INDEX mf_sentence_score_comment ON mf_sentence_score (ruleset_version, comment_id);
CREATE INDEX mf_sentence_score_text_key ON mf_sentence_score (text_key);

CREATE TABLE mf_sentence_hit (
    hit_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ruleset_version TEXT NOT NULL,
    unit_id         INTEGER NOT NULL,
    run_id          INTEGER NOT NULL,
    dimension       TEXT NOT NULL,
    grade           INTEGER NOT NULL,
    rule            TEXT NOT NULL,
    match           TEXT NOT NULL,
    start_char      INTEGER NOT NULL,
    end_char        INTEGER NOT NULL
);
CREATE INDEX mf_sentence_hit_unit ON mf_sentence_hit (ruleset_version, unit_id);
CREATE INDEX mf_sentence_hit_rule ON mf_sentence_hit (ruleset_version, rule);

CREATE TABLE mf_comment_score (
    ruleset_version TEXT NOT NULL,
    comment_id      TEXT NOT NULL,
    run_id          INTEGER NOT NULL,
    place INTEGER NOT NULL, stand INTEGER NOT NULL, doc INTEGER NOT NULL, gap INTEGER NOT NULL,
    evid INTEGER NOT NULL, ask INTEGER NOT NULL, alt INTEGER NOT NULL, law INTEGER NOT NULL,
    strength        INTEGER NOT NULL,
    gate            INTEGER NOT NULL,
    gate_basis      TEXT NOT NULL,
    band            TEXT NOT NULL,
    moves           TEXT NOT NULL,
    targets         TEXT NOT NULL,
    sentence_count  INTEGER NOT NULL,
    prong_impacts      INTEGER NOT NULL DEFAULT 0 CHECK (prong_impacts IN (0, 1)),
    prong_significance INTEGER NOT NULL DEFAULT 0 CHECK (prong_significance IN (0, 1)),
    prong_alternatives INTEGER NOT NULL DEFAULT 0 CHECK (prong_alternatives IN (0, 1)),
    prong_compliance   INTEGER NOT NULL DEFAULT 0 CHECK (prong_compliance IN (0, 1)),
    prong_impacts_basis      TEXT NOT NULL DEFAULT '[]',
    prong_significance_basis TEXT NOT NULL DEFAULT '[]',
    prong_alternatives_basis TEXT NOT NULL DEFAULT '[]',
    prong_compliance_basis   TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (ruleset_version, comment_id)
);

CREATE TABLE mf_comment_answerability (
    ruleset_version TEXT NOT NULL,
    comment_id      TEXT NOT NULL,
    run_id          INTEGER NOT NULL,
    level           TEXT NOT NULL,
    defeated        TEXT NOT NULL,
    open            TEXT NOT NULL,
    mechanism       INTEGER NOT NULL,
    cite            INTEGER NOT NULL,
    PRIMARY KEY (ruleset_version, comment_id)
);

-- ===========================================================================
-- 9c. make score-model-compare (scripts/score_model_compare.py; new). One row
--     per comparison run and one per comment per method, so every comparison
--     is kept and any two runs can be set side by side in the console. A run
--     is stamped with the code it ran (the git commit, and whether the working
--     tree had uncommitted changes), the model and server, the instrument and
--     the rule set. Written by that command only; the scoring steps' tables are
--     not touched by it.
-- ===========================================================================

CREATE TABLE score_compare_run (
    run_id             TEXT PRIMARY KEY,       -- compare/<run_id>/, YYYYMMDD_HHMMSS
    started_at         TEXT NOT NULL,
    finished_at        TEXT,
    code_version       TEXT NOT NULL,          -- git rev-parse HEAD
    code_dirty         INTEGER NOT NULL,       -- 1: tracked files had uncommitted changes
    model              TEXT NOT NULL,
    server             TEXT NOT NULL,          -- the base URL the calls went to
    instrument_version TEXT NOT NULL,
    ruleset_version    TEXT NOT NULL,
    comments_of        TEXT REFERENCES score_compare_run (run_id),  -- the run whose comments were read again
    pool               INTEGER NOT NULL,       -- class A comments the model reads as themselves
    picked             INTEGER NOT NULL,
    report             TEXT                    -- the printed comparison, model against rules
);

CREATE TABLE score_compare_reading (
    run_id     TEXT NOT NULL REFERENCES score_compare_run (run_id),
    comment_id TEXT NOT NULL,
    method     TEXT NOT NULL CHECK (method IN ('model', 'model-free')),
    record     TEXT,                           -- shared/score_json.py's shape; NULL when the call failed
    error      TEXT,
    PRIMARY KEY (run_id, comment_id, method)
);

-- ===========================================================================
-- 10. Attachments
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
-- by each attachment's longest rendition (ranked by row_number; ties by format
-- name, as ORDER BY chars DESC, fmt).
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
-- 11. Campaign organisations
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
-- 12. The vocabulary; rows from seeds/vocabulary.csv
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

-- ===========================================================================
-- 13. The sentences of the gate set, for the clusters and topics (scripts/clusters/).
--     make sentences reads
--     the model-free reading (section 9b) of the comments whose hybrid gate is
--     open, in the screen classes asked for (A and B1 by
--     default), and writes each sentence occurrence and each
--     distinct sentence (its text_key). A rebuild replaces both tables; the run
--     row keeps the counts of every build.
-- ===========================================================================

CREATE TABLE gate_sentence_run (
    run_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    ruleset_version      TEXT    NOT NULL,
    classes              TEXT    NOT NULL,       -- the screen classes read, e.g. A,B1
    created_at           TEXT    NOT NULL,
    gate_comments        INTEGER NOT NULL,       -- comments whose hybrid gate is open
    occurrences          INTEGER NOT NULL,       -- their sentences
    distinct_sentences   INTEGER NOT NULL,
    comments_opening     INTEGER NOT NULL,       -- with a sentence that opens the gate alone
    comments_hit         INTEGER NOT NULL,       -- with a sentence that holds a whole-comment gate hit
    comments_neither     INTEGER NOT NULL,       -- with neither
    sentences_unlocated  INTEGER NOT NULL,       -- sentences not found in the whole comment's text
    hits_unlocated       INTEGER NOT NULL        -- whole-comment gate hits in no located sentence
);

CREATE TABLE gate_sentence_occurrence (
    unit_id    INTEGER PRIMARY KEY,               -- mf_sentence_score.unit_id
    text_key   TEXT    NOT NULL,
    comment_id TEXT    NOT NULL,
    law        INTEGER NOT NULL,                  -- 1: the sentence reaches 2 on the dimension
    evid       INTEGER NOT NULL,
    gap        INTEGER NOT NULL,
    alt        INTEGER NOT NULL,
    opens      INTEGER NOT NULL,                  -- 1: the sentence opens the gate alone
    holds_hit  INTEGER NOT NULL                   -- 1: it holds a gate hit of the whole comment
);
CREATE INDEX gate_sentence_occurrence_key ON gate_sentence_occurrence (text_key);
CREATE INDEX gate_sentence_occurrence_comment ON gate_sentence_occurrence (comment_id);

CREATE TABLE gate_sentence (
    text_key    TEXT    PRIMARY KEY,              -- sha256 of the sentence's norm_key
    text        TEXT    NOT NULL,                 -- the smallest of its texts in sort order
    occurrences INTEGER NOT NULL,
    comments    INTEGER NOT NULL,
    law         INTEGER NOT NULL,                 -- 1 when any occurrence has it
    evid        INTEGER NOT NULL,
    gap         INTEGER NOT NULL,
    alt         INTEGER NOT NULL,
    opens       INTEGER NOT NULL,
    holds_hit   INTEGER NOT NULL
);

-- One vector for each distinct sentence, model and instruction (make embed,
-- scripts/clusters/embed.py). The vector is
-- 1,024 little-endian float32; input_sha256 is the SHA-256 of the exact string
-- sent (the instruction and the text), so a vector made another way is never
-- taken for this one. Not keyed to a sentence build: a sentence keeps its
-- vector across builds.
CREATE TABLE sentence_embedding (
    text_key     TEXT    NOT NULL,
    model        TEXT    NOT NULL,
    instruction  TEXT    NOT NULL,              -- '' for the plain text
    input_sha256 TEXT    NOT NULL,
    dimensions   INTEGER NOT NULL,
    vector       BLOB    NOT NULL,
    created_at   TEXT    NOT NULL,
    PRIMARY KEY (text_key, model, instruction)
);

-- The record documents (make docindex, scripts/docindex/ingest_documents.py):
-- the Draft EIS volumes, the Biological Assessments, the Economic Analysis,
-- the notices, the Tribal Summary Impact Statement and the orders, their
-- sections, their chunks and the chunks' vectors.
--
--   doc_documents         one row per source file; sha256 of the markdown so a
--                         re-ingest of changed text is detectable.
--   doc_sections          the document split by its heading tree (or letter
--                         boundaries for the agency-letters volume);
--                         heading_path is the recovered nesting, root first,
--                         as a JSON array. Offsets are character offsets into
--                         the source file.
--   doc_chunks            fixed-size overlapping windows of a section's text,
--                         the unit that is embedded; offsets into the source
--                         file, so a match cites back to the exact passage.
--   doc_chunk_embeddings  one row per chunk per model, vectors packed as
--                         sentence_embedding packs them, so a document chunk
--                         and a comment sentence embedded by the same model
--                         compare directly.

CREATE TABLE doc_documents (
    document_id  INTEGER PRIMARY KEY,
    title        TEXT    NOT NULL,
    source_file  TEXT    NOT NULL UNIQUE,
    sha256       TEXT    NOT NULL,
    n_chars      INTEGER NOT NULL,
    ingested_at  TEXT    NOT NULL
);

CREATE TABLE doc_sections (
    section_id    INTEGER PRIMARY KEY,
    document_id   INTEGER NOT NULL REFERENCES doc_documents (document_id) ON DELETE CASCADE,
    ordinal       INTEGER NOT NULL,
    heading_path  TEXT    NOT NULL,          -- JSON array, root first
    kind          TEXT    NOT NULL,          -- front | toc | body | letter
    start_char    INTEGER NOT NULL,
    end_char      INTEGER NOT NULL,
    section_text  TEXT    NOT NULL,
    page_start    INTEGER,                   -- source pages spanned, from the page map
    page_end      INTEGER,
    UNIQUE (document_id, ordinal)
);

CREATE TABLE doc_chunks (
    chunk_id        INTEGER PRIMARY KEY,
    section_id      INTEGER NOT NULL REFERENCES doc_sections (section_id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    chunk_text      TEXT    NOT NULL,
    start_char      INTEGER NOT NULL,
    end_char        INTEGER NOT NULL,
    max_chunk_size  INTEGER NOT NULL,
    chunk_overlap   INTEGER NOT NULL,
    page_start      INTEGER,
    page_end        INTEGER,
    UNIQUE (section_id, chunk_index)
);

CREATE TABLE doc_chunk_embeddings (
    chunk_id              INTEGER NOT NULL REFERENCES doc_chunks (chunk_id) ON DELETE CASCADE,
    embedding             BLOB    NOT NULL,
    embedding_model       TEXT    NOT NULL,
    embedding_dimensions  INTEGER NOT NULL,
    token_count           INTEGER,
    created_at            TEXT    NOT NULL,
    PRIMARY KEY (chunk_id, embedding_model)
);

-- The clustering cases (make clusters, scripts/clusters/cases.py). A case is one
-- value on each axis: the sentences, the view, the merge, the reduction, the
-- HDBSCAN settings, the structure, the noise passes, the topic cut, the seed.
-- Its name is made from its values; a run of a case replaces that case's rows
-- and no other. The case row holds its values, its stamp and its measures.
CREATE TABLE cluster_case (
    case_name                     TEXT    PRIMARY KEY,
    sentences                     TEXT    NOT NULL CHECK (sentences IN ('opening', 'opening+hits', 'all')),
    view                          TEXT    NOT NULL,
    model                         TEXT    NOT NULL,
    merge                         REAL    NOT NULL,           -- leader-merge cosine; 0 for none
    reduction                     TEXT    NOT NULL CHECK (reduction IN ('pca50', 'umap5', 'pacmap5')),
    min_cluster_size              INTEGER NOT NULL,
    min_samples                   INTEGER NOT NULL,
    selection                     TEXT    NOT NULL CHECK (selection IN ('eom', 'leaf')),
    structure                     TEXT    NOT NULL CHECK (structure IN ('all', 'by-kind', 'by-prong')),
    noise_passes                  INTEGER NOT NULL,
    k                             INTEGER,                    -- the topic cut asked for; NULL: the largest eigengap
    seed                          INTEGER NOT NULL,
    sentence_run_id               INTEGER NOT NULL,           -- the gate_sentence_run it read
    code_version                  TEXT    NOT NULL,
    code_dirty                    INTEGER NOT NULL,
    created_at                    TEXT    NOT NULL,
    seconds                       REAL    NOT NULL,
    input_sentences               INTEGER NOT NULL,           -- distinct sentences read
    occurrences                   INTEGER NOT NULL,
    leaders                       INTEGER NOT NULL,
    clusters                      INTEGER NOT NULL,
    topics                        INTEGER NOT NULL,
    eigengaps                     TEXT    NOT NULL,           -- JSON [[k, gap], ...], largest first
    leaders_clustered             INTEGER NOT NULL,
    occurrences_clustered         INTEGER NOT NULL,
    largest_cluster               INTEGER NOT NULL,           -- leaders
    gate_comments                 INTEGER NOT NULL,
    comments_unclustered          INTEGER NOT NULL,           -- gate-open comments with no sentence in a cluster
    opening_occurrences           INTEGER NOT NULL,           -- sentences that open the gate alone
    -- all-but-the-top: top_removed is the components removed before the merge
    -- (NULL: no correction, 0: the centring alone); top_variance is JSON, the
    -- share of variance of the top 10 components, when the correction ran
    opening_occurrences_clustered INTEGER NOT NULL,
    top_removed                   INTEGER,
    top_variance                  TEXT
);

CREATE TABLE cluster_case_leader (
    case_name  TEXT NOT NULL,
    text_key   TEXT NOT NULL,                     -- a sentence the case read
    leader_key TEXT NOT NULL,                     -- the sentence that stands for it after the merge
    PRIMARY KEY (case_name, text_key)
);
CREATE INDEX cluster_case_leader_leader ON cluster_case_leader (case_name, leader_key);

CREATE TABLE cluster_case_member (
    case_name  TEXT    NOT NULL,
    leader_key TEXT    NOT NULL,
    kind       TEXT    NOT NULL,                  -- '' when the structure is all; LAW, EVID, GAP or ALT when by kind; the prong when by prong
    cluster    INTEGER NOT NULL,                  -- 0 for noise
    PRIMARY KEY (case_name, leader_key, kind)
);
CREATE INDEX cluster_case_member_cluster ON cluster_case_member (case_name, cluster);

CREATE TABLE cluster_case_cluster (
    case_name   TEXT    NOT NULL,
    cluster     INTEGER NOT NULL,                 -- 1.. by size, largest first
    kind        TEXT    NOT NULL,
    pass        INTEGER NOT NULL,                 -- 1 for the first pass; 2.. for a noise pass
    topic       INTEGER NOT NULL,
    leaders     INTEGER NOT NULL,
    variants    INTEGER NOT NULL,                 -- sentences the leaders absorbed
    occurrences INTEGER NOT NULL,
    tightness   REAL    NOT NULL,                 -- mean cosine of its leaders to its centroid
    law         REAL    NOT NULL,                 -- the share of its leaders of each gate kind
    evid        REAL    NOT NULL,
    gap         REAL    NOT NULL,
    alt         REAL    NOT NULL,
    terms       TEXT    NOT NULL,                 -- JSON, eight distinctive terms
    central     TEXT    NOT NULL,                 -- JSON, the two sentences nearest its centroid
    PRIMARY KEY (case_name, cluster)
);

CREATE TABLE cluster_case_topic (
    case_name   TEXT    NOT NULL,
    topic       INTEGER NOT NULL,                 -- 1.. by occurrences, largest first
    clusters    INTEGER NOT NULL,
    leaders     INTEGER NOT NULL,
    occurrences INTEGER NOT NULL,
    terms       TEXT    NOT NULL,
    PRIMARY KEY (case_name, topic)
);

-- The case chosen for each embedding model (make choose, scripts/clusters/cases.py choose):
-- stage 4 of docs/topics-guide.md picks the best case of each model; stage 5 compares
-- the two choices. One row per model; a new choice replaces the old one.
CREATE TABLE cluster_case_choice (
    model      TEXT PRIMARY KEY,
    case_name  TEXT NOT NULL,
    note       TEXT,
    chosen_at  TEXT NOT NULL
);

-- The concern map (make concern-map, scripts/clusters/cases.py concern-map): stage 5 of
-- docs/topics-guide.md decides between the two choices of stage 4, and the decided case is the
-- clustering that the later steps read. One row; a new decision replaces the old one.
CREATE TABLE cluster_concern_map (
    one        INTEGER PRIMARY KEY CHECK (one = 1),
    case_name  TEXT NOT NULL,
    note       TEXT,
    decided_at TEXT NOT NULL
);
