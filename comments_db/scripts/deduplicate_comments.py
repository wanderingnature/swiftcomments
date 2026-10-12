#!/usr/bin/env python3
"""
Main script for deduplicating comments in a project's analysis schema.
Identifies duplicate comments and upserts them into the comment_dedup table.
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict

# comments_db root (src imports) and repo root (shared.project_context)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))   # repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))          # comments_db (must precede repo root: both have a src package)

from shared.project_context import ProjectContext, add_project_argument, context_from_args
from src.preprocessing.text_processor import TextProcessor
from src.utils.database import (
    DatabaseConnection,
    fetch_all_comments,
    update_comment_deduplication,
    get_deduplication_stats,
    get_top_duplicates
)

# Setup logging (file handler added in main once the project context is known)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CommentDeduplicator:
    """Handles the deduplication process for comments."""

    def __init__(self, ctx: ProjectContext, dry_run: bool = False):
        """
        Initialize the deduplicator.

        Args:
            ctx: ProjectContext
            dry_run: If True, don't update database, just report findings
        """
        self.ctx = ctx
        self.dry_run = dry_run
        self.text_processor = TextProcessor()
        self.stats = {
            'total_comments': 0,
            'unique_comments': 0,
            'duplicate_comments': 0,
            'duplicate_groups': 0,
            'largest_group': 0,
            'processing_time': 0
        }

    def deduplicate_comments(self, min_length: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Main deduplication process.

        Args:
            min_length: Minimum comment length to process

        Returns:
            List of update records for the database
        """
        start_time = datetime.now()

        # Fetch all comments
        logger.info("Fetching comments from database...")
        comments = fetch_all_comments(self.ctx, min_length=min_length)
        logger.info(f"Fetched {len(comments)} comments")

        self.stats['total_comments'] = len(comments)

        # Process each comment to generate hashes
        logger.info("Generating content hashes...")
        hash_groups = defaultdict(list)  # hash -> list of comments
        comment_hashes = {}  # comment_id -> (sha256, md5)

        for i, comment in enumerate(comments):
            if i > 0 and i % 10000 == 0:
                logger.info(f"Processed {i}/{len(comments)} comments...")

            # Generate hashes
            sha256_hash, md5_hash = self.text_processor.get_hashes(comment['comment_text'])

            if sha256_hash:  # Only process if we got a valid hash
                comment_hashes[comment['comment_id']] = (sha256_hash, md5_hash)
                hash_groups[sha256_hash].append(comment)

        logger.info(f"Found {len(hash_groups)} unique content hashes")

        # Identify duplicate groups and prepare updates
        logger.info("Identifying duplicate groups...")
        updates = []

        for content_hash, group_comments in hash_groups.items():
            group_size = len(group_comments)

            if group_size > self.stats['largest_group']:
                self.stats['largest_group'] = group_size

            if group_size > 1:
                self.stats['duplicate_groups'] += 1

            # Sort by comment_id to get the "original" (first occurrence)
            group_comments.sort(key=lambda x: x['comment_id'])
            original_comment = group_comments[0]

            # Create update records for all comments in the group
            for i, comment in enumerate(group_comments):
                sha256_hash, md5_hash = comment_hashes[comment['comment_id']]

                is_original = (i == 0)  # First comment is the original

                update_record = {
                    'comment_id': comment['comment_id'],
                    'content_hash': sha256_hash,
                    'content_hash_md5': md5_hash,
                    'is_original': is_original,
                    'original_comment_id': None if is_original else original_comment['comment_id'],
                    'duplicate_group_size': group_size
                }

                updates.append(update_record)

                if is_original:
                    self.stats['unique_comments'] += 1
                else:
                    self.stats['duplicate_comments'] += 1

        # Calculate processing time
        end_time = datetime.now()
        self.stats['processing_time'] = int((end_time - start_time).total_seconds())

        logger.info(f"Deduplication analysis complete:")
        logger.info(f"  Total comments: {self.stats['total_comments']}")
        logger.info(f"  Full-text originals: {self.stats['unique_comments']}")
        logger.info(f"  Duplicate comments: {self.stats['duplicate_comments']}")
        logger.info(f"  Duplicate groups: {self.stats['duplicate_groups']}")
        logger.info(f"  Largest group: {self.stats['largest_group']}")
        logger.info(f"  Processing time: {self.stats['processing_time']:.2f} seconds")

        return updates

    def update_database(self, updates: List[Dict[str, Any]]):
        """
        Update the database with deduplication information.

        Args:
            updates: List of update records
        """
        if self.dry_run:
            logger.info("DRY RUN mode - not updating database")
            return

        logger.info(f"Updating {len(updates)} records in database...")
        try:
            records_updated = update_comment_deduplication(self.ctx, updates)
            logger.info(f"Successfully updated {records_updated} records")
        except Exception as e:
            logger.error(f"Failed to update database: {e}")
            raise

    def print_report(self):
        """Print a detailed report of the deduplication results."""
        print("\n" + "=" * 80)
        print("DEDUPLICATION REPORT")
        print("=" * 80)

        # Get stats from database
        db_stats = get_deduplication_stats(self.ctx)
        if db_stats and db_stats.get('total_comments'):
            print("\nDatabase Statistics:")
            print(f"  Total comments: {db_stats['total_comments']:,}")
            print(f"  Full-text originals: {db_stats.get('unique_comments', 0) or 0:,}"
                  " (a hash count, not the reported unique count:"
                  " docs/reference/uniqueness-measures.md)")
            print(f"  Duplicate comments: {db_stats.get('duplicate_comments', 0) or 0:,}")
            if db_stats.get('duplicate_percentage'):
                print(f"  Duplicate percentage: {db_stats['duplicate_percentage']:.2f}%")
            print(f"  Distinct hashes: {db_stats.get('distinct_hashes', 0) or 0:,}")
            if db_stats.get('largest_duplicate_group'):
                print(f"  Largest duplicate group: {db_stats['largest_duplicate_group']:,}")
        else:
            print("\nDatabase Statistics: No deduplication data found yet (run without --dry-run to update)")

        # Get top duplicates
        print("\nTop 10 Most Duplicated Comments:")
        print("-" * 80)
        top_dupes = get_top_duplicates(self.ctx, limit=10)
        for i, dupe in enumerate(top_dupes, 1):
            print(f"\n{i}. Duplicated {dupe['duplicate_group_size']:,} times")
            print(f"   Hash (SHA256): {dupe['content_hash']}")
            print(f"   Hash (MD5): {dupe['content_hash_md5']}")
            print(f"   Length: {dupe['comment_length']:,} characters")
            print(f"   Sample ID: {dupe['sample_comment_id']}")
            print(f"   Preview: {dupe['comment_preview']}")

        print("\n" + "=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Deduplicate comments in the analysis schema'
    )
    add_project_argument(parser)
    parser.add_argument(
        '--min-length',
        type=int,
        help='Minimum comment length to process'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show analysis of existing deduplication data without processing'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Only show report of existing deduplication data'
    )

    args = parser.parse_args()

    ctx = context_from_args(args)

    # Per-project log file
    ctx.logs_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(ctx.logs_dir / 'deduplication.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)

    # Create deduplicator
    deduplicator = CommentDeduplicator(ctx, dry_run=args.dry_run)

    try:
        if args.report_only:
            # Just show the report
            logger.info("Generating report from existing data...")
            deduplicator.print_report()

        else:
            # Check if this is a dry run
            if args.dry_run:
                # Just show what would be processed
                logger.info("DRY RUN - Checking what would be processed...")

                # Get count of comments that would be processed
                logger.info("Fetching comment count...")
                comments = fetch_all_comments(ctx, min_length=args.min_length)

                logger.info(f"\nDRY RUN Summary:")
                logger.info(f"  Would process {len(comments):,} comments")
                if args.min_length:
                    logger.info(f"  With minimum length: {args.min_length}")
                logger.info(f"\nRun without --dry-run to perform actual deduplication")
            else:
                # Full deduplication process
                logger.info("Starting comment deduplication process...")

                # Perform deduplication
                updates = deduplicator.deduplicate_comments(min_length=args.min_length)

                # Update database
                if updates:
                    deduplicator.update_database(updates)

                # Show report
                deduplicator.print_report()

                logger.info("Deduplication process complete")

    except Exception as e:
        logger.error(f"Deduplication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()