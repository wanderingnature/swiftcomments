#!/usr/bin/env python3
"""
Deduplicate comments based on middle content analysis.
This is a second-stage deduplication that finds form letters with different salutations/closings.
"""

import sys
import os
import argparse
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from collections import defaultdict
from datetime import datetime
import logging

# comments_db root (src imports) and repo root (shared.project_context)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))   # repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))          # comments_db (must precede repo root: both have a src package)

from shared.project_context import ProjectContext, add_project_argument, context_from_args
from shared.text_norm import unescape_text
from src.preprocessing.text_processor import TextProcessor
from src.utils.database import DatabaseConnection

# Setup logging (file handler added in main once the project context is known)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def _one(cur):
    """The single row a query must return. No row means the query is wrong, so it fails here
    rather than subscripting None."""
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("expected one row, got none")
    return row


class MiddleContentDeduplicator:
    """Performs second-stage deduplication based on partial content."""

    def __init__(self, ctx: ProjectContext, chars: int = 500, mode: str = 'trim-end', dry_run: bool = False):
        """
        Initialize deduplicator.

        Args:
            ctx: ProjectContext
            chars: Number of characters to use/skip depending on mode
            mode: Extraction mode ('first', 'last', or 'trim-end')
            dry_run: If True, don't update database
        """
        self.ctx = ctx
        self.chars = chars
        self.mode = mode
        self.dry_run = dry_run
        self.text_processor = TextProcessor()
        self.stats = {
            'original_comments': 0,
            'new_duplicates_found': 0,
            'middle_unique_count': 0,
            'middle_dup_groups': 0
        }

    def extract_middle_content(self, text: str) -> str:
        """Extract content based on the selected mode."""
        if not text:
            return ""

        text_length = len(text)

        if self.mode == 'first':
            # Take first N characters only (ignore endings)
            if text_length <= self.chars:
                return text.strip()
            return text[:self.chars].strip()

        elif self.mode == 'last':
            # Take last N characters only (ignore beginnings)
            if text_length <= self.chars:
                return text.strip()
            return text[-self.chars:].strip()

        elif self.mode == 'trim-end':
            # Take everything except last N characters (ignore signatures)
            if text_length <= self.chars + 20:  # Need some content left
                return ""
            return text[:-self.chars].strip()

        else:
            raise ValueError(f"Invalid mode: {self.mode}")

    def get_middle_hash(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get MD5 hash of middle content.

        Returns:
            Tuple of (middle_text, md5_hash)
        """
        # The window is cut by character count, so the form's markup has to
        # go before the cut: a '<br/>' in one copy and not another would move
        # the cut and hash the two apart however the window is canonicalized.
        middle_text = self.extract_middle_content(unescape_text(text or ""))

        if not middle_text:
            return None, None

        normalized_middle = self.text_processor.get_canonical_text(middle_text)

        if not normalized_middle:
            return middle_text, None

        md5_hash = hashlib.md5(normalized_middle.encode('utf-8')).hexdigest()
        return middle_text, md5_hash

    def deduplicate_by_middle_content(self, min_length: int = 120):
        """
        Main deduplication process for middle content.

        Args:
            min_length: Minimum comment length to process
        """
        start_time = datetime.now()

        # Fetch comments that are unique by both full text and middle content
        logger.info(f"Fetching truly unique comments with length >= {min_length}...")

        query = """
            SELECT
                c.comment_id,
                c.comment_text,
                c.comment_length,
                ci.content_hash,
                ci.duplicate_group_size
            FROM {analysis}.v_truly_unique_comments v
            INNER JOIN {analysis}.v_source_comments c ON v.comment_id = c.comment_id
            INNER JOIN {analysis}.comment_dedup ci ON c.comment_id = ci.comment_id
            WHERE c.comment_length >= ?
            ORDER BY c.comment_id
        """

        from src.utils.database import get_db_cursor

        with get_db_cursor(self.ctx, dict_cursor=True) as cur:
            cur.execute(query, [min_length])
            comments = cur.fetchall()
            comments = [dict(row) for row in comments]

        logger.info(f"Fetched {len(comments)} original comments")
        self.stats['original_comments'] = len(comments)

        # Process middle content
        logger.info("Analyzing middle content...")
        middle_hash_groups = defaultdict(list)
        skipped = 0

        for i, comment in enumerate(comments):
            if i > 0 and i % 10000 == 0:
                logger.info(f"Processed {i}/{len(comments)} comments...")

            middle_text, middle_hash = self.get_middle_hash(comment['comment_text'])

            if not middle_hash:
                skipped += 1
                continue

            middle_hash_groups[middle_hash].append(comment)

        logger.info(f"Found {len(middle_hash_groups)} unique middle content hashes")
        logger.info(f"Skipped {skipped} comments (too short for middle analysis)")

        # Identify new duplicate groups
        updates = []
        new_duplicates = 0

        # EVERY computed hash is persisted, including a group of one. The hash
        # was already computed for the whole population; writing it only when
        # group_size > 1 threw away 81,813 of them on roadless and left the
        # column unreadable — NULL meant both "never processed" and "processed,
        # no middle twin", and nothing could tell them apart. A group of one IS
        # the finding for those comments.
        for middle_hash, group_comments in middle_hash_groups.items():
            group_size = len(group_comments)

            if group_size > 1:
                self.stats['middle_dup_groups'] += 1

            # Sort by comment_id to get the first as "original"
            group_comments.sort(key=lambda x: x['comment_id'])
            middle_original = group_comments[0]

            # Create update records
            for i, comment in enumerate(group_comments):
                is_middle_original = (i == 0)

                update_record = {
                    'comment_id': comment['comment_id'],
                    'middle_content_hash': middle_hash,
                    'is_middle_original': is_middle_original,
                    'middle_original_id': None if is_middle_original else middle_original['comment_id'],
                    'middle_dup_group_size': group_size
                }

                updates.append(update_record)

                if not is_middle_original:
                    new_duplicates += 1

        self.stats['new_duplicates_found'] = new_duplicates
        self.stats['middle_unique_count'] = len(comments) - new_duplicates

        # Calculate processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Report results
        logger.info(f"\nMiddle content deduplication complete:")
        logger.info(f"  Original comments analyzed: {self.stats['original_comments']:,}")
        logger.info(f"  Middle-content originals: {self.stats['middle_unique_count']:,}")
        logger.info(f"  New duplicates found: {self.stats['new_duplicates_found']:,}")
        logger.info(f"  Duplicate groups: {self.stats['middle_dup_groups']:,}")
        logger.info(f"  Processing time: {processing_time:.2f} seconds")

        return updates

    def update_database(self, updates: List[Dict[str, Any]]):
        """Update database with middle content deduplication."""
        if self.dry_run:
            logger.info("DRY RUN mode - not updating database")
            return

        if not updates:
            logger.info("No updates to perform")
            return

        logger.info(f"Updating {len(updates)} records in database...")

        update_query = """
            UPDATE {analysis}.comment_dedup
            SET
                middle_content_hash = :middle_content_hash,
                is_middle_original = :is_middle_original,
                middle_original_id = :middle_original_id,
                middle_dup_group_size = :middle_dup_group_size,
                middle_hash_updated_at = :middle_hash_updated_at
            WHERE comment_id = :comment_id
        """

        # Add timestamp
        timestamp = datetime.now().isoformat(sep=' ', timespec='seconds')
        for update in updates:
            update['middle_hash_updated_at'] = timestamp

        db = DatabaseConnection(self.ctx)
        conn = db.connect()
        try:
            with conn.cursor() as cur:
                cur.executemany(self.ctx.render_sql(update_query), updates)
                conn.commit()
                logger.info(f"Successfully updated {len(updates)} records")
        except Exception as e:
            logger.error(f"Failed to update database: {e}")
            conn.rollback()
            raise
        finally:
            db.close()

    def print_report(self):
        """Print detailed report of middle content deduplication."""
        print("\n" + "=" * 80)
        print("MIDDLE CONTENT DEDUPLICATION REPORT")
        if self.mode == 'first':
            print(f"(Compared first {self.chars} characters)")
        elif self.mode == 'last':
            print(f"(Compared last {self.chars} characters)")
        else:  # trim-end
            print(f"(Excluded last {self.chars} characters)")
        print("=" * 80)

        # Get updated statistics from database
        query = """
            SELECT
                COUNT(*) as total_original,
                SUM(CASE WHEN is_middle_original THEN 1 ELSE 0 END) as middle_unique,
                SUM(CASE WHEN NOT is_middle_original THEN 1 ELSE 0 END) as middle_duplicates,
                COUNT(DISTINCT middle_content_hash) as distinct_middle_hashes,
                MAX(middle_dup_group_size) as largest_middle_group
            FROM {analysis}.comment_dedup
            WHERE is_original = true
                AND middle_content_hash IS NOT NULL
        """

        from src.utils.database import get_db_cursor

        try:
            with get_db_cursor(self.ctx, dict_cursor=True) as cur:
                cur.execute(query)
                stats = dict(cur.fetchone())

                if stats and stats['total_original']:
                    print("\nDatabase Statistics (Original Comments Only):")
                    print(f"  Total original comments processed: {stats['total_original']:,}")
                    print(f"  Middle-content originals: {stats['middle_unique']:,}")
                    print(f"  Form letter duplicates: {stats['middle_duplicates']:,}")

                    reduction_pct = 100.0 * stats['middle_duplicates'] / stats['total_original']
                    print(f"  Additional reduction: {reduction_pct:.1f}%")

                    print(f"  Distinct middle hashes: {stats['distinct_middle_hashes']:,}")
                    print(f"  Largest form letter group: {stats['largest_middle_group']:,}")

                    # Get combined statistics
                    combined_query = """
                        SELECT
                            COUNT(*) as total_comments,
                            SUM(CASE WHEN is_original AND (is_middle_original = true OR is_middle_original IS NULL) THEN 1 ELSE 0 END) as truly_unique,
                            SUM(CASE WHEN NOT is_original THEN 1 ELSE 0 END) as full_text_dups,
                            SUM(CASE WHEN is_original AND is_middle_original = false THEN 1 ELSE 0 END) as form_letter_dups
                        FROM {analysis}.comment_dedup
                        WHERE content_hash IS NOT NULL
                    """

                    cur.execute(combined_query)
                    combined = dict(cur.fetchone())

                    if combined:
                        print("\nCombined Deduplication Results:")
                        print(f"  Total comments: {combined['total_comments']:,}")
                        print(f"  Full-text duplicates: {combined['full_text_dups']:,}")
                        print(f"  Form letter duplicates: {combined['form_letter_dups']:,}")
                        print(f"  Pass both hash passes: {combined['truly_unique']:,}")
                        print("  (hash counts, not the reported unique count: that is one per comment"
                              " group, printed by the comment-groups step)")

                        total_dups = combined['full_text_dups'] + combined['form_letter_dups']
                        overall_reduction = 100.0 * total_dups / combined['total_comments']
                        print(f"  Overall duplicate rate: {overall_reduction:.1f}%")

        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            print(f"\nError generating report: {e}")

        print("\n" + "=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Perform second-stage deduplication based on partial content comparison'
    )
    add_project_argument(parser)
    parser.add_argument(
        '--min-length',
        type=int,
        default=100,
        help='Minimum comment length to process (default: 100)'
    )
    parser.add_argument(
        '--chars',
        type=int,
        default=50,
        help='Number of characters to use/skip based on mode (default: 50)'
    )
    parser.add_argument(
        '--mode',
        choices=['first', 'last', 'trim-end'],
        default='trim-end',
        help='Extraction mode: first N chars, last N chars, or trim last N chars (default: trim-end)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show count of what would be processed without any processing'
    )
    parser.add_argument(
        '--eval',
        action='store_true',
        help='Evaluate mode: perform full analysis and show results without updating database'
    )

    args = parser.parse_args()

    ctx = context_from_args(args)

    # Per-project log file
    ctx.logs_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(ctx.logs_dir / 'middle_deduplication.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)

    # Create deduplicator
    deduplicator = MiddleContentDeduplicator(
        ctx,
        chars=args.chars,
        mode=args.mode,
        dry_run=args.dry_run
    )

    try:
        if args.dry_run:
            # Just show what would be processed
            logger.info("DRY RUN - Checking what would be processed...")

            # Count truly unique comments that would be analyzed
            query = """
                SELECT COUNT(*)
                FROM {analysis}.v_truly_unique_comments v
                INNER JOIN {analysis}.v_source_comments c ON v.comment_id = c.comment_id
                WHERE c.comment_length >= :min_length
            """

            with DatabaseConnection(ctx) as db:
                conn = db.connect()
                with conn.cursor() as cur:
                    cur.execute(ctx.render_sql(query), {"min_length": args.min_length})
                    count = _one(cur)[0]

            logger.info(f"\nDRY RUN Summary:")
            logger.info(f"  Would analyze {count:,} original comments")
            logger.info(f"  Minimum length: {args.min_length}")
            if args.mode == 'first':
                logger.info(f"  Mode: Compare first {args.chars} characters")
            elif args.mode == 'last':
                logger.info(f"  Mode: Compare last {args.chars} characters")
            else:
                logger.info(f"  Mode: Exclude last {args.chars} characters")
            logger.info(f"\nRun without --dry-run to perform actual deduplication")

        elif args.eval:
            # Evaluation mode - do full processing but don't update database
            logger.info("EVALUATION MODE - Performing analysis without database updates...")

            # Run deduplication analysis
            updates = deduplicator.deduplicate_by_middle_content(
                min_length=args.min_length
            )

            # Show evaluation results
            logger.info(f"\nEVALUATION RESULTS:")
            logger.info(f"  Mode: {args.mode}")
            if args.mode == 'first':
                logger.info(f"  Compared first {args.chars} characters")
            elif args.mode == 'last':
                logger.info(f"  Compared last {args.chars} characters")
            else:
                logger.info(f"  Excluded last {args.chars} characters")
            logger.info(f"  Original comments analyzed: {deduplicator.stats['original_comments']:,}")
            logger.info(f"  New duplicates found: {deduplicator.stats['new_duplicates_found']:,}")
            logger.info(f"  Duplicate groups: {deduplicator.stats['middle_dup_groups']:,}")
            logger.info(f"  Would remain middle-content originals: {deduplicator.stats['middle_unique_count']:,}")

            # Calculate percentage
            if deduplicator.stats['original_comments'] > 0:
                dup_rate = 100.0 * deduplicator.stats['new_duplicates_found'] / deduplicator.stats['original_comments']
                logger.info(f"  Duplicate rate: {dup_rate:.1f}%")

            logger.info(f"\nRun without --eval to perform actual database update")

        else:
            # Run full deduplication
            updates = deduplicator.deduplicate_by_middle_content(
                min_length=args.min_length
            )

            # Update database
            if updates:
                deduplicator.update_database(updates)

            # Print report
            deduplicator.print_report()

            logger.info("Middle content deduplication complete")

    except Exception as e:
        logger.error(f"Deduplication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()