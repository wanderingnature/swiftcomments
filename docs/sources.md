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
