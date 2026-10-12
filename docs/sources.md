# Sources

Every file of this repository that comes from rtca, with its path there at the tag
`reproduction-source`, and every file that is new. A ported file keeps its
original's structure and names and changes only what the port to SQLite requires;
the commit that added it says what changed.

| file here | rtca source at the tag | what changed |
|---|---|---|
| `seeds/entity_tagging/seed_legal_authority.csv` | `db/seeds/entity_tagging/seed_legal_authority.csv` | copied |
| `seeds/entity_tagging/seed_reference.csv` | `db/seeds/entity_tagging/seed_reference.csv` | copied |
| `seeds/entity_tagging/seed_places.csv` | `db/seeds/entity_tagging/seed_places.csv` | copied |
| `seeds/forests.csv` | the `roadless.forests` table on DEV, 122 rows, read once on 2026-10-12 | new file; `load_references.py --source-dbname` built it from the upstream roadless database |
| `seeds/roadless_areas.csv` | `roadless.roadless_areas` on DEV, 2,331 rows, read once on 2026-10-12 | new file, as above |
| `seeds/species.csv` | `roadless.species` on DEV, 357 rows, read once on 2026-10-12 | new file, as above |
| `seeds/roadless_profile.sql` | `db/seeds/roadless_profile.sql` | for SQLite: `{analysis}.` dropped, `ARRAY[...]` as JSON text; the rtca header dropped |
| `seeds/roadless_prompt_v2.sql` | `db/seeds/roadless_prompt_v2.sql` | for SQLite: `{analysis}.` and `::jsonb` dropped, the `$tpl$` template as a quoted string, two adjacent literals joined; the rtca header dropped |
| `seeds/vocabulary.csv` | the `INSERT INTO roadless.vocabulary` rows of `db/migrations_pending/roadless_vocabulary.sql`, `roadless_family_organisation.sql`, `roadless_comment_organisation.sql`, `roadless_vocabulary_composition.sql` | 57 rows, as CSV |
| `scripts/substance/vocab/*.txt`, `vocab/topics/*.txt` | `scripts/substance/vocab/` | copied, at the path `grade.py` reads |
| `docs/reviews/campaign-organisations-2026-10-11.md` | `docs/reviews/campaign-organisations-2026-10-11.md` | copied, at the path `campaign_organisations.py` reads |
| `docs/reviews/attachment-bundles-by-organisation-2026-10-08.md` | `docs/reviews/attachment-bundles-by-organisation-2026-10-08.md` | copied, at the path `attachment_accounting.py` reads |
| `tests/fixtures/authority_family_key.csv` | `roadless.authority_family_key(citation)` on DEV over every `legal_authority` and `comment_authorities` citation, 447 distinct, read once on 2026-10-12 | new file; the oracle for the Python port of the function |
| `schema/roadless.sql` | `db/project_template/01, 02, 09, 10, 11, 12, 13, 22, 23, 24, 25, 28`; `db/migrations_pending/roadless_dynamic_views.sql`, `roadless_comment_group_analysis_comment_id.sql`, `roadless_attachment_ocr.sql`, `substance_screen.sql`, `substance_answerability.sql` (+ `_view_gated`), `roadless_comment_organisation.sql`, `roadless_family_organisation.sql`, `roadless_vocabulary.sql` | written for SQLite, the tables the steps write and the views they read only (plan 4.3); the translations are listed in the file's header; `comment` and `attachment_file` are new |
| `shared/db.py` | new; `authority_family_key` is `roadless.authority_family_key` of `db/migrations_pending/roadless_dynamic_views.sql`, pattern for pattern | the one SQLite-aware module (plan 5.2) |
| `scripts/make_schema.py` | new | creates the file from the DDL, loads the profile seeds and the vocabulary |
| `tests/test_db.py` | new; the three regexes are `CITATION_RE`, `DEFICIENCY_RE`, `FIRSTPERSON_RE` of `scripts/substance/floor_filter.py` | |
| `scripts/load_csv.py` | new (plan 3.1) | the loader of the bulk download |
| `tests/test_load_csv.py`, `tests/fixtures/bulk_cut.csv` | new; the fixture is twenty records of the bulk download | |
| `shared/text_norm.py` | `shared/text_norm.py` | copied, byte for byte |
| `shared/near_duplicates.py` | `shared/near_duplicates.py` | copied, byte for byte |
| `shared/project_context.py` | `shared/project_context.py` | plan 4.2: a dataclass of constants in place of the registry row; `render_sql` renders `{analysis}.` and `{src}.` to nothing; `db_config` is the SQLite path and `dict_connect` opens through `shared/db.py`; `psycopg`, the env-driven DB config, the schema-name checks and `dict_connect_dsn` gone |
| `shared/instrument.py` | `shared/instrument.py` | plan 5.2 edit 8: the serving-name table, `SCORING_MODELS`, the endpoint rates and `gpu_rate_per_min` gone; `configured_model()` reads `LLM_MODEL`; `model_of`, `weights_of`, `same_weights`, `is_measured_model` keep their names over the one name |
| `shared/llm_client.py` | `shared/llm_client.py` | plan 5.2 edit 8: the server and the model from `LLM_BASE_URL` and `LLM_MODEL`, a Bearer header from `LLM_API_KEY` only; the by-host key lookup, the OpenRouter provider pin, the dedicated-endpoint names and the Fireworks scale-up retries gone; thinking off with both spellings |
| `comments_db/src/__init__.py`, `src/utils/__init__.py`, `src/extractors/__init__.py`, `src/preprocessing/__init__.py` | the same paths | copied (the package markers) |
| `comments_db/src/utils/logger.py` | `comments_db/src/utils/logger.py` | copied, byte for byte |
| `comments_db/src/config.py` | `comments_db/src/config.py` | copied, byte for byte |
| `comments_db/src/preprocessing/text_processor.py` | `comments_db/src/preprocessing/text_processor.py` | copied, byte for byte |
| `comments_db/src/extractors/long_ngram_extractor.py` | `comments_db/src/extractors/long_ngram_extractor.py` | copied, byte for byte |
| `tests/substance/test_long_ngram_extractor.py` | `tests/substance/test_long_ngram_extractor.py` | copied, byte for byte |
| `comments_db/src/utils/database.py` | `comments_db/src/utils/database.py` | plan 5.2 edit 5: trimmed to `DatabaseConnection`, the cursor helpers and the four dedup helpers; `psycopg` and `pgvector` gone, connections through `shared/db.py`; `%(name)s` to `:name`, `NOW()` to `CURRENT_TIMESTAMP`, `LEFT` to `substr` |
| `src/__init__.py`, `src/pipeline/__init__.py`, `src/utils/__init__.py` | the same paths | copied |
| `src/pipeline/paths.py` | `src/pipeline/paths.py` | copied, byte for byte |
| `src/utils/logging_config.py` | `src/utils/logging_config.py` | copied, byte for byte |
| `src/pipeline/profile.py` | `src/pipeline/profile.py` | connection through `shared/db.py`, `%s` to `?`, `IS NOT DISTINCT FROM` to `IS`, `model_parameters` parsed from JSON text; the two error messages name `make schema` instead of the rtca seed |
| `comments_db/scripts/deduplicate_comments.py` | `comments_db/scripts/deduplicate_comments.py` | copied, byte for byte (its SQL lives in `database.py`) |
| `comments_db/scripts/deduplicate_middle_content.py` | `comments_db/scripts/deduplicate_middle_content.py` | `%s` and `%(name)s` placeholders; the timestamp bound as ISO-8601 text; and the rtca defect at line 39, `_one` calling itself, replaced by `cur.fetchone()` (reported for rtca) |
