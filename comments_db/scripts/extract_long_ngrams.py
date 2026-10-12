#!/usr/bin/env python3
"""
Batch extraction script for long n-grams (6-8 words)
Processes comments from the database and persists n-grams for analysis
"""

import sys
import json
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Set
from pathlib import Path
import hashlib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))   # repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))          # comments_db (must precede repo root: both have a src package)

from src.extractors.long_ngram_extractor import LongNgramExtractor
from shared.project_context import dict_connect, ProjectContext, add_project_argument, context_from_args

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NgramDatabaseProcessor:
    """Handle database operations for n-gram extraction and persistence."""

    def __init__(self, ctx: ProjectContext):
        """Initialize database connection."""
        self.ctx = ctx
        self.conn = None
        self.cursor = None
        self.batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Every n-gram this run mapped a comment to, new or pre-existing. Its
        # statistics are the only ones that can have changed, so the end-of-run
        # statistics and template flags are recomputed for these alone. Until
        # 2026-09-23 both statements covered the whole table — 9.45 million
        # rows, 2.9 GB, rewritten every hour for a few hundred new comments —
        # and the hourly run sat in them for 15+ minutes with nothing logged.
        self.touched_ngram_ids: set[int] = set()

    def connect(self):
        """Establish database connection."""
        try:
            self.conn = dict_connect(self.ctx.db_config)
            self.cursor = self._conn().cursor()
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise


    def _cur(self):
        """The open cursor, or a clear error. self.cursor stays None until connect() runs, so
        a query before that names the cause instead of failing on None."""
        if self.cursor is None:
            raise RuntimeError("Not connected — call connect() first.")
        return self.cursor


    def _conn(self):
        """The open connection, or a clear error. self.conn stays None until connect() runs."""
        if self.conn is None:
            raise RuntimeError("Not connected — call connect() first.")
        return self.conn

    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")

    def rebuild(self):
        """Empty every table derived from the n-grams, so a full extraction
        starts clean. One TRUNCATE names all five because they reference each
        other; template_blocks and comment_templates are rebuilt afterwards
        by analyze_templates.py --detect-blocks. The detector's
        duplicate_groups are keyed by comment, not n-gram, and are rebuilt by
        its own --rebuild."""
        for table in ("comment_long_ngrams", "long_ngram_stats", "comment_templates",
                      "template_blocks", "long_ngrams"):
            self._cur().execute(self.ctx.render_sql("DELETE FROM {analysis}." + table))
        self._conn().commit()
        logger.info("Rebuild: n-gram, stats and template tables emptied")

    def pending_ids(self, skip_duplicates: bool = True, rebuild: bool = False) -> List[str]:
        """The comment ids to extract, in id order: the population (originals
        over 100 characters, or every comment with --include-duplicates) minus
        the comments that already have n-gram rows. After --rebuild nothing
        has rows, so this is the whole population.

        Fetched ONCE as an id list, then processed in batches by id. The
        previous loop paged the population with OFFSET, which cannot skip
        already-extracted comments: a comment that yields no n-grams (fewer
        than six tokens) never gains a row and would be re-fetched forever."""
        source = "v_unique_comments" if skip_duplicates else "v_source_comments"
        query = (
            "SELECT v.comment_id FROM {analysis}." + source + " v"
            " WHERE v.comment_text IS NOT NULL AND LENGTH(v.comment_text) > 100"
            + ("" if rebuild else
               " AND NOT EXISTS (SELECT 1 FROM {analysis}.comment_long_ngrams n"
               "                 WHERE n.comment_id = v.comment_id)")
            + " ORDER BY v.comment_id")
        self._cur().execute(self.ctx.render_sql(query))
        ids = [row['comment_id'] for row in self._cur().fetchall()]
        logger.info(f"{len(ids)} comment(s) to extract from {source}")
        return ids

    def fetch_comments(self, ids: List[str]) -> List[Dict]:
        """The texts of these comment ids, in the ids' order."""
        if not ids:
            return []
        self._cur().execute(self.ctx.render_sql(
            "SELECT comment_id, comment_text FROM {analysis}.v_source_comments"
            " WHERE comment_id IN (SELECT value FROM json_each(?))"), (json.dumps(ids),))
        by_id = {row['comment_id']: row for row in self._cur().fetchall()}
        return [by_id[c] for c in ids if c in by_id]

    def insert_ngrams(self, ngram_data: List[Dict]) -> Dict[str, int]:
        """
        Insert unique n-grams into database.

        Args:
            ngram_data: List of n-gram information dictionaries

        Returns:
            Mapping of n-gram hash to ngram_id
        """
        # Prepare unique n-grams for insertion
        unique_ngrams = {}
        for item in ngram_data:
            ng_hash = item['hash']
            if ng_hash not in unique_ngrams:
                unique_ngrams[ng_hash] = {
                    'hash': ng_hash,
                    'text': item['text'],
                    'n': item['n'],
                    'word_count': item['n'],
                    'first_words': item.get('first_words', ''),
                    'last_words': item.get('last_words', '')
                }

        if not unique_ngrams:
            return {}

        # Insert n-grams using ON CONFLICT DO NOTHING (without RETURNING)
        insert_query = self.ctx.render_sql("""
        INSERT INTO {analysis}.long_ngrams
        (ngram_hash, ngram_text, n, word_count, first_words, last_words)
        VALUES (:hash, :text, :n, :word_count, :first_words, :last_words)
        ON CONFLICT (ngram_hash) DO NOTHING
        """)

        ngram_values = list(unique_ngrams.values())

        try:
            # One round trip per batch, not one per n-gram: a full rebuild
            # inserts 8.5 million rows, and the per-row loop this replaced
            # also ran COUNT(*) over the table after every batch.
            self._cur().executemany(insert_query, ngram_values)
            self._conn().commit()
            logger.info(f"Upserted {len(ngram_values)} n-gram(s)")

            # Now fetch all IDs (both new and pre-existing)
            hashes = list(unique_ngrams.keys())

            # PostgreSQL has a limit of 65535 parameters, so batch if needed
            hash_to_id = {}
            batch_size = 10000  # Safe batch size well under the limit

            for i in range(0, len(hashes), batch_size):
                batch_hashes = hashes[i:i + batch_size]
                self._cur().execute(self.ctx.render_sql(
                    "SELECT ngram_hash, ngram_id FROM {analysis}.long_ngrams"
                    " WHERE ngram_hash IN (SELECT value FROM json_each(?))"), (json.dumps(batch_hashes),))
                for row in self._cur().fetchall():
                    hash_to_id[row['ngram_hash']] = row['ngram_id']

            unresolved = [h for h in hashes if h not in hash_to_id]
            if unresolved:
                raise RuntimeError(
                    f"{len(unresolved)} n-gram(s) have no id after the upsert — the insert"
                    " and the lookup disagree. All of them:\n  " + "\n  ".join(
                        f"{h} {unique_ngrams[h]['text']!r}" for h in unresolved))
            self.touched_ngram_ids.update(hash_to_id.values())
            return hash_to_id

        except Exception as e:
            logger.error(f"Failed to insert n-grams: {e}")
            raise

    def insert_comment_ngrams(self, comment_ngrams: List[Dict]):
        """
        Insert comment-n-gram mappings.

        Args:
            comment_ngrams: List of comment-n-gram relationships
        """
        if not comment_ngrams:
            return

        # One executemany in one transaction (COPY in rtca), not one INSERT per
        # row: a rebuild writes 40 million occurrences. No ON CONFLICT is
        # needed — a comment is extracted only when it has no rows
        # (pending_ids), and within one comment the (ngram_id, position) pair
        # is unique by construction, since the same tokens at the same
        # position are the same n-gram.
        try:
            self._cur().executemany(self.ctx.render_sql(
                    "INSERT INTO {analysis}.comment_long_ngrams"
                    " (comment_id, ngram_id, position, sentence_position,"
                    "  char_start, char_end) VALUES (?, ?, ?, ?, ?, ?)"),
                [(m['comment_id'], m['ngram_id'], m['position'],
                  m['sentence_position'], m['char_start'],
                  m['char_end']) for m in comment_ngrams])
            self._conn().commit()
            logger.info(f"Inserted {len(comment_ngrams)} comment-n-gram mappings")
        except Exception as e:
            logger.error(f"Failed to insert comment-n-gram mappings: {e}")
            raise

    def update_ngram_stats(self):
        """Update n-gram statistics based on current data."""
        # document_frequency counts DISTINCT TEXTS: the population is one
        # original per exact class, so an 11,453-copy letter counts once.
        # comment_frequency weights each original by its class size, which is
        # the count the family builder's distinctive test needs (R1 in
        # docs/reviews/shared-text-detection-review.md). Only originals carry
        # weight: under --include-duplicates a copy's own row is already
        # counted inside its original's duplicate_group_size.
        stats_query = """
        INSERT INTO {analysis}.long_ngram_stats
            (ngram_id, document_frequency, comment_frequency, total_frequency,
             avg_position, std_position)
        SELECT
            n.ngram_id,
            COUNT(DISTINCT cn.comment_id) as document_frequency,
            COALESCE(SUM(d.duplicate_group_size) FILTER (WHERE d.is_original), 0)
                as comment_frequency,
            COUNT(*) as total_frequency,
            AVG(cn.position) as avg_position,
            STDDEV(cn.position) as std_position
        FROM {analysis}.long_ngrams n
        JOIN {analysis}.comment_long_ngrams cn ON n.ngram_id = cn.ngram_id
        LEFT JOIN {analysis}.comment_dedup d ON d.comment_id = cn.comment_id
        WHERE n.ngram_id IN (SELECT value FROM json_each(?))
        GROUP BY n.ngram_id
        ON CONFLICT (ngram_id) DO UPDATE SET
            document_frequency = EXCLUDED.document_frequency,
            comment_frequency = EXCLUDED.comment_frequency,
            total_frequency = EXCLUDED.total_frequency,
            avg_position = EXCLUDED.avg_position,
            std_position = EXCLUDED.std_position,
            updated_at = CURRENT_TIMESTAMP
        """

        ids = sorted(self.touched_ngram_ids)
        if not ids:
            logger.info("No n-gram touched this run — statistics unchanged")
            return
        logger.info(f"Updating statistics for the {len(ids):,} n-gram(s) this run touched...")
        try:
            # Explicit commit: conn.transaction() only makes a savepoint when an
            # implicit transaction is already open, and close() would roll it back
            self._cur().execute(self.ctx.render_sql(stats_query), (json.dumps(ids),))
            self._conn().commit()
            logger.info(f"Updated statistics for {len(ids):,} n-gram(s)")
        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")
            raise

    def mark_template_candidates(self, min_doc_frequency: int = 5):
        """
        Mark n-grams as template candidates based on frequency.

        Args:
            min_doc_frequency: Minimum document frequency for template candidate
        """
        # Only an n-gram whose document_frequency this run recomputed can
        # change flag. The predicate this replaced — ngram_id IN (SELECT
        # ngram_id FROM the same table) — matched every row.
        update_query = """
        UPDATE {analysis}.long_ngram_stats
        SET
            is_template_candidate = (document_frequency >= ?),
            template_confidence = min(1.0, CAST(document_frequency AS REAL) / 100)
        WHERE ngram_id IN (SELECT value FROM json_each(?))
        """
        ids = sorted(self.touched_ngram_ids)
        if not ids:
            logger.info("No n-gram touched this run — template flags unchanged")
            return
        logger.info(f"Updating template flags for {len(ids):,} n-gram(s)...")
        try:
            self._cur().execute(self.ctx.render_sql(update_query), (min_doc_frequency, json.dumps(ids)))
            self._conn().commit()
            logger.info(f"Updated template flags for {len(ids):,} n-gram(s)")
        except Exception as e:
            logger.error(f"Failed to mark template candidates: {e}")
            raise

    def log_processing(self, comments_processed: int, ngrams_extracted: int, status: str = 'completed'):
        """Log processing batch information."""
        log_query = """
        INSERT INTO {analysis}.long_ngram_processing_log
        (batch_id, comments_processed, ngrams_extracted, start_time, end_time, status)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        """

        try:
            self._cur().execute(self.ctx.render_sql(log_query), (
                self.batch_id,
                comments_processed,
                ngrams_extracted,
                datetime.now().isoformat(sep=' ', timespec='seconds'),
                status
            ))
            self._conn().commit()
        except Exception as e:
            logger.error(f"Failed to log processing: {e}")


def process_batch(processor: NgramDatabaseProcessor, extractor: LongNgramExtractor,
                  comments: List[Dict]) -> Dict[str, int]:
    """
    Process a batch of comments.

    Args:
        processor: Database processor instance
        extractor: N-gram extractor instance
        comments: List of comments to process

    Returns:
        Statistics about the batch processing
    """
    all_ngram_data = []
    all_comment_ngrams = []

    # Track stopword filtering effectiveness
    total_before_filter = 0
    total_after_filter = 0

    for comment in comments:
        comment_id = comment['comment_id']
        text = comment['comment_text']

        # Extract n-grams with positions (stopword filtering happens here)
        # First get unfiltered count for comparison
        ngrams_unfiltered = extractor.extract_with_positions(text, filter_stopword_redundancy=False)
        ngrams_filtered = extractor.extract_with_positions(text, filter_stopword_redundancy=True)

        # Count n-grams before and after filtering
        before = sum(len(ng_list) for ng_list in ngrams_unfiltered.values())
        after = sum(len(ng_list) for ng_list in ngrams_filtered.values())
        total_before_filter += before
        total_after_filter += after

        for n, ngram_list in ngrams_filtered.items():
            for ng_info in ngram_list:
                # Collect n-gram data
                ng_data = {
                    'hash': ng_info['hash'],
                    'text': ng_info['text'],
                    'n': n,
                    'first_words': ng_info['first_words'],
                    'last_words': ng_info['last_words']
                }
                all_ngram_data.append(ng_data)

                # Store for comment-n-gram mapping (will get ID later)
                all_comment_ngrams.append({
                    'comment_id': comment_id,
                    'hash': ng_info['hash'],
                    'position': ng_info['position'],
                    'sentence_position': ng_info['sentence_position'],
                    'char_start': ng_info['char_start'],
                    'char_end': ng_info['char_end'],
                })

    # Log stopword filtering effectiveness for this batch
    if total_before_filter > 0:
        reduction_pct = ((total_before_filter - total_after_filter) / total_before_filter) * 100
        logger.info(f"Stopword filtering: {total_before_filter} -> {total_after_filter} n-grams "
                   f"({total_before_filter - total_after_filter} dropped, {reduction_pct:.1f}% reduction)")

    # Insert n-grams and get ID mapping
    hash_to_id = processor.insert_ngrams(all_ngram_data)

    # Update comment-n-gram mappings with actual IDs. insert_ngrams raises
    # when a hash has no id, so every mapping resolves.
    comment_ngram_records = [{
        'comment_id': mapping['comment_id'],
        'ngram_id': hash_to_id[mapping['hash']],
        'position': mapping['position'],
        'sentence_position': mapping['sentence_position'],
        'char_start': mapping['char_start'],
        'char_end': mapping['char_end'],
    } for mapping in all_comment_ngrams]

    # Insert comment-n-gram mappings
    processor.insert_comment_ngrams(comment_ngram_records)

    return {
        'total_ngrams': len(all_ngram_data),
        'unique_ngrams': len(set(ng['hash'] for ng in all_ngram_data)),
        'new_ngrams': len(hash_to_id),
        'mappings': len(comment_ngram_records),
        'stopword_filtered': total_before_filter - total_after_filter
    }


def main():
    parser = argparse.ArgumentParser(description='Extract long n-grams from comments')
    add_project_argument(parser)
    parser.add_argument('--batch-size', type=int, default=100,
                        help='Number of comments to process per batch')
    parser.add_argument('--limit', type=int, default=None,
                        help='Total number of comments to process')
    parser.add_argument('--offset', type=int, default=0,
                        help='Number of comments to skip')
    parser.add_argument('--min-n', type=int, default=6,
                        help='Minimum n-gram size')
    parser.add_argument('--max-n', type=int, default=8,
                        help='Maximum n-gram size')
    parser.add_argument('--min-doc-freq', type=int, default=5,
                        help='Minimum document frequency for template candidates')
    parser.add_argument('--update-stats', action='store_true',
                        help='Update statistics after processing')
    parser.add_argument('--include-duplicates', action='store_true',
                        help='Process all comments including known duplicates')
    parser.add_argument('--rebuild', action='store_true',
                        help='Empty the n-gram, stats and template tables first and extract'
                             ' the whole population (default: only comments with no rows yet)')

    args = parser.parse_args()

    ctx = context_from_args(args)

    # Initialize processor and extractor
    processor = NgramDatabaseProcessor(ctx)
    extractor = LongNgramExtractor(
        min_n=args.min_n,
        max_n=args.max_n,
        remove_stopwords=False,  # Keep all words for template detection
        lowercase=True
    )

    try:
        processor.connect()
        if args.rebuild:
            processor.rebuild()

        # The id list once, then batches by id (see pending_ids). --offset and
        # --limit slice that list.
        ids = processor.pending_ids(skip_duplicates=not args.include_duplicates,
                                    rebuild=args.rebuild)
        ids = ids[args.offset:]
        if args.limit:
            ids = ids[:args.limit]

        total_processed = 0
        total_ngrams = 0
        for start in range(0, len(ids), args.batch_size):
            comments = processor.fetch_comments(ids[start:start + args.batch_size])
            logger.info(f"Processing batch of {len(comments)} comments"
                        f" ({start + len(comments)} of {len(ids)})")
            batch_stats = process_batch(processor, extractor, comments)

            total_processed += len(comments)
            total_ngrams += batch_stats['total_ngrams']

            # Log meaningful batch statistics
            logger.info(f"Batch stats: {batch_stats['unique_ngrams']} unique, "
                       f"{batch_stats['new_ngrams']} new to DB, "
                       f"{batch_stats['mappings']} mappings created")
            logger.info(f"Overall progress: {total_processed} comments processed, "
                       f"{total_ngrams} total n-grams extracted")

        # Update statistics if requested
        if args.update_stats:
            logger.info("Updating n-gram statistics...")
            processor.update_ngram_stats()
            processor.mark_template_candidates(args.min_doc_freq)

        # Log completion
        processor.log_processing(total_processed, total_ngrams, 'completed')
        logger.info(f"Extraction complete: {total_processed} comments, {total_ngrams} n-grams")

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        processor.log_processing(0, 0, 'failed')
        raise
    finally:
        processor.close()


if __name__ == "__main__":
    main()
