#!/usr/bin/env python3
"""
Extract Linguistic Patterns from Comments - Phase 2 Syntactic Analysis

INCREMENTAL: processes only comments of the population that have no named
entities yet, so a second run touches only comments not done, not the whole
corpus. The population is the floor filter's base set (plan 5.2, edit 3): the
originals of v_truly_unique_comments longer than 100 characters. Extracts, per
comment:
- Named entities (spaCy NER)

Table: {analysis}.named_entities. It has a surrogate PK and no (comment_id, ...)
dedup constraint, so the incremental filter is load-bearing — reprocessing a
comment DUPLICATES its rows. The id list is fetched ONCE and processed in
batches by id; a comment with no entities gets no rows and is simply read again
by a later run, which writes nothing for it.

A first-time (full-corpus) run is ~30-40 comments/sec with spaCy.
"""

import json
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Optional, List, Tuple

import spacy
import numpy as np
from tqdm import tqdm

# comments_db root (src imports) and repo root (shared.project_context)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))   # repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))          # comments_db (must precede repo root: both have a src package)

from shared.project_context import ProjectContext, add_project_argument, context_from_args
from src.utils.database import DatabaseConnection

logger = logging.getLogger(__name__)

# Constants
BATCH_SIZE = 100


def setup_logging(ctx: ProjectContext):
    """Configure logging with the project's log directory."""
    ctx.logs_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(ctx.logs_dir / 'extract_linguistic_patterns.log'),
            logging.StreamHandler()
        ]
    )


def extract_patterns(comment_id: str, doc) -> Dict[str, List[Dict]]:
    """
    Extract all linguistic patterns from spaCy doc.

    Returns dict with 1 list: named_entities
    """
    patterns = {
        'named_entities': []
    }

    # Named entities from spaCy NER
    for ent in doc.ents:
        patterns['named_entities'].append({
            'comment_id': comment_id,
            'entity_text': ent.text.strip().lower(),  # Normalize to lowercase
            'entity_type': ent.label_,
            'char_start': ent.start_char,
            'char_end': ent.end_char
        })

    return patterns


def insert_patterns_batch(db: DatabaseConnection, all_patterns: Dict):
    """Insert accumulated patterns in bulk."""

    # Named entities
    if all_patterns['named_entities']:
        query = """
            INSERT INTO {analysis}.named_entities
            (comment_id, entity_text, entity_type, char_start, char_end)
            VALUES (?, ?, ?, ?, ?)
        """
        tuples = [(p['comment_id'], p['entity_text'], p['entity_type'],
                   p['char_start'], p['char_end'])
                  for p in all_patterns['named_entities']]
        db.execute_many(query, tuples)


def pending_ids(db: DatabaseConnection, random: bool = False) -> List[str]:
    """
    The comment ids whose named entities are NOT yet extracted, fetched ONCE.

    The population is the floor's base set: v_truly_unique_comments with
    length(comment_text) > 100 (plan 5.2, edit 2). "Not yet extracted" = no
    named_entities row. A comment that yielded no entities has no row either
    and is read again by a later run, which writes nothing for it; a comment
    with rows is never read twice, which is what keeps these surrogate-PK rows
    from being DUPLICATED.

    Args:
        db: Database connection
        random: If True, order randomly instead of by comment_id (testing only)

    Returns:
        List of comment ids
    """
    order = "ORDER BY RANDOM()" if random else "ORDER BY v.comment_id"
    query = f"""
        SELECT v.comment_id
        FROM {{analysis}}.v_truly_unique_comments v
        WHERE length(v.comment_text) > 100
          AND NOT EXISTS (SELECT 1 FROM {{analysis}}.named_entities e
                          WHERE e.comment_id = v.comment_id)
        {order}
    """
    return [row[0] for row in db.fetch(query)]


def fetch_comments(db: DatabaseConnection, ids: List[str]) -> List[Tuple[str, str]]:
    """The texts of these comment ids, in the ids' order."""
    rows = db.fetch(
        "SELECT comment_id, comment_text FROM {analysis}.v_source_comments"
        " WHERE comment_id IN (SELECT value FROM json_each(?))", (json.dumps(ids),))
    by_id = {row[0]: row[1] for row in rows}
    return [(c, by_id[c]) for c in ids if c in by_id]


def process_comments(ctx: ProjectContext, dry_run: bool = False, limit: Optional[int] = None, random_sample: bool = False):
    """
    Main processing function.

    Args:
        ctx: Project context (schemas, DB config)
        dry_run: If True, process but don't write to database
        limit: Maximum number of comments to process (for testing)
        random_sample: If True, fetch random sample instead of sequential
    """
    # Load spaCy model (using same model as existing pipeline)
    logger.info("Loading spaCy model...")
    nlp = spacy.load("en_core_web_md", disable=["textcat"])
    logger.info(f"spaCy model loaded: {nlp.meta['name']} v{nlp.meta['version']}")
    logger.info(f"Active pipes: {nlp.pipe_names}")

    # Initialize database connection
    db = DatabaseConnection(ctx)

    # Dry run mode
    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No database writes will be performed")
        logger.info("=" * 60)

    # This step is INCREMENTAL: it processes only comments of the population with no
    # named_entities row (pending_ids), fetched once as an id list and worked in
    # batches by id. `resume` is implicit: every run starts from what the table lacks.
    # NOTE: named_entities has a surrogate PK and no (comment_id, ...) dedup constraint,
    # so processing a comment with entities twice DUPLICATES its rows — the filter is
    # load-bearing, not merely an optimization.
    ids = pending_ids(db, random=random_sample)
    if limit:
        logger.info(f"--limit {limit}: the first {min(limit, len(ids)):,} of {len(ids):,} pending"
                    " comments; run without --limit for the rest, or make jump STEP=ner"
                    " for our run's rows")
        ids = ids[:limit]
    total_unprocessed = len(ids)
    logger.info(f"Unprocessed comments (no named_entities row): {total_unprocessed}"
                f" (dry run: {dry_run})")
    if total_unprocessed == 0:
        logger.info("Nothing to do — every comment already has named entities.")
        return

    # Statistics
    start_time = time.time()
    processed_count = 0
    batch_times = []
    pattern_stats = {
        'named_entities': 0
    }

    remaining = total_unprocessed
    with tqdm(total=total_unprocessed, desc="Processing comments") as pbar:
        for start in range(0, len(ids), BATCH_SIZE):
            batch_start = time.time()
            try:
                comments = fetch_comments(db, ids[start:start + BATCH_SIZE])
                if not comments:
                    break

                texts = [text for _, text in comments]
                comment_ids = [cid for cid, _ in comments]

                all_patterns = {
                    'named_entities': []
                }

                for comment_id, doc in zip(comment_ids, nlp.pipe(texts, batch_size=50)):
                    patterns = extract_patterns(comment_id, doc)
                    for key in all_patterns:
                        all_patterns[key].extend(patterns[key])
                        pattern_stats[key] += len(patterns[key])

                # Insert patterns (skip writes in dry run).
                if not dry_run:
                    insert_patterns_batch(db, all_patterns)

                n = len(comments)
                processed_count += n
                remaining -= n

                batch_time = time.time() - batch_start
                batch_times.append(batch_time)
                avg_time = np.mean(batch_times[-10:])
                pbar.update(n)
                pbar.set_postfix({
                    'comments/sec': f'{n / batch_time:.1f}',
                    'ETA': f'{(remaining / BATCH_SIZE) * avg_time / 60:.1f}m'
                })

                # Dry run writes nothing: one batch is the measurement.
                if dry_run:
                    break

            except Exception as e:
                logger.error(f"Fatal error processing batch: {e}")
                raise

    # Final report
    total_time = time.time() - start_time
    logger.info("=" * 60)
    if dry_run:
        logger.info("DRY RUN COMPLETE - Pattern Extraction Summary")
    else:
        logger.info("Linguistic Pattern Extraction Complete")
    logger.info("=" * 60)
    logger.info(f"Total comments processed: {processed_count}")
    logger.info(f"Total time: {total_time / 60:.1f} minutes")
    logger.info(f"Average speed: {processed_count / total_time:.1f} comments/sec")

    logger.info("-" * 60)
    logger.info("Pattern Statistics:")
    logger.info("-" * 60)
    for key, count in pattern_stats.items():
        avg_per_comment = count / processed_count if processed_count > 0 else 0
        logger.info(f"{key:20s}: {count:8d} total ({avg_per_comment:.1f} avg/comment)")

    if dry_run:
        logger.info("-" * 60)
        logger.info("Performance Metrics:")
        logger.info("-" * 60)
        logger.info(f"Estimated full runtime: {(total_time / processed_count * total_unprocessed) / 60:.1f} minutes")
        logger.info(f"Estimated full runtime: {(total_time / processed_count * total_unprocessed) / 3600:.1f} hours")

    logger.info("=" * 60)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Extract linguistic patterns from comments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run with 100 random comments to test performance
  python extract_linguistic_patterns.py --dry-run --limit 100 --random

  # Dry run with first 1000 comments
  python extract_linguistic_patterns.py --dry-run --limit 1000

  # Full production run (incremental: only comments not yet processed)
  python extract_linguistic_patterns.py
        """
    )
    parser.add_argument('--dry-run', action='store_true', help='Process without writing to database (for testing)')
    parser.add_argument('--limit', type=int, help='Limit number of comments to process (for testing)')
    parser.add_argument('--random', action='store_true', help='Use random sample instead of sequential (requires --limit)')
    add_project_argument(parser)
    args = parser.parse_args()

    # Validate arguments
    if args.random and not args.limit:
        parser.error("--random requires --limit to be specified")

    ctx = context_from_args(args)
    setup_logging(ctx)

    logger.info("Starting linguistic pattern extraction")
    logger.info(f"Batch size: {BATCH_SIZE}")
    logger.info(f"Dry run mode: {args.dry_run}")
    if args.limit:
        logger.info(f"Limit: {args.limit} comments")
    if args.random:
        logger.info(f"Random sampling: enabled")

    try:
        process_comments(
            ctx,
            dry_run=args.dry_run,
            limit=args.limit,
            random_sample=args.random
        )
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user. Re-run to resume — it is incremental "
                       "(only unprocessed comments are picked up).")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
