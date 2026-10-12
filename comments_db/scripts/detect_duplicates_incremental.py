#!/usr/bin/env python3
"""
Incremental duplicate detection that excludes already-found duplicates.
Keeps one representative from each group for matching with new tolerance levels.

Grouping is LEADER ASSIGNMENT (shared/near_duplicates.py): texts in a
size bucket are visited in a fixed order and each one joins the leader it
overlaps most, at or above the threshold, or becomes a leader. Every member
is therefore within the threshold of its own leader, which union-find could
not promise: A~B and B~C merged A with C whether or not A~C, and the only
check for that was sampling pairs afterwards. The leader is the group's
representative.

Similarity is the overlap coefficient, intersection over the smaller set,
inside buckets of equal n-gram count (+/- --match), so it behaves as
resemblance there. Population is comment_long_ngrams, one original text per
exact-duplicate class; each text's weight is its class size
(comment_dedup.duplicate_group_size), and heavier texts lead.
"""

import sys
import os
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple
from collections import defaultdict
import time
import json
import hashlib

# comments_db root (src imports) and repo root (shared.project_context)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))   # repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))          # comments_db (must precede repo root: both have a src package)

from shared.project_context import dict_connect, ProjectContext, add_project_argument, context_from_args
from shared.near_duplicates import SimpleBloomFilter, assign_leaders  # noqa: F401  (the Bloom filter is re-exported for its callers)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _one(cur):
    """The single row a query must return. No row means the query is wrong."""
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("expected one row, got none")
    return row


def expansion_target(leader, matching_reps, representatives):
    """The one stored group a cluster expands: the group whose representative
    leads the cluster. `representatives` is group_id -> representative id.
    Falls back to the first matching representative's group only when the
    leader is not one, which assign_leaders' seeded ordering rules out."""
    by_rep = {rid: gid for gid, rid in representatives.items()}
    if leader in by_rep:
        return by_rep[leader]
    for rep_id in matching_reps:
        if rep_id in by_rep:
            return by_rep[rep_id]
    return None


class IncrementalDuplicateDetector:
    """Detect duplicates incrementally, excluding already-found matches."""

    def __init__(self, ctx: ProjectContext):
        """Initialize with project context."""
        self.ctx = ctx
        self.conn = None
        self.cursor = None
        self.excluded_comments = set()
        self.representatives = {}  # group_id -> representative_comment_id
        self.stored = {'expanded': 0, 'members_added': 0, 'new': 0, 'skipped': 0}

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

    def load_existing_groups(self):
        """Load existing duplicate groups from database."""
        logger.info("Loading existing duplicate groups...")

        # Get all group members
        self._cur().execute(self.ctx.render_sql("""
            SELECT dgm.group_id, dgm.comment_id, dgm.is_representative
            FROM {analysis}.duplicate_group_members dgm
            JOIN {analysis}.duplicate_groups dg ON dgm.group_id = dg.group_id
            WHERE dg.group_size >= 2
        """))

        groups_by_id = defaultdict(list)
        for row in self._cur().fetchall():
            groups_by_id[row['group_id']].append({
                'comment_id': row['comment_id'],
                'is_representative': row['is_representative']
            })

        # Process each group
        for group_id, members in groups_by_id.items():
            # Find representative (or pick first if none marked)
            representative = None
            for member in members:
                if member['is_representative']:
                    representative = member['comment_id']
                    break
            if representative is None:
                representative = members[0]['comment_id']

            self.representatives[group_id] = representative

            # Exclude all members except representative
            for member in members:
                if member['comment_id'] != representative:
                    self.excluded_comments.add(member['comment_id'])

        logger.info(f"Loaded {len(groups_by_id)} existing groups")
        logger.info(f"Excluding {len(self.excluded_comments)} duplicate comments")
        logger.info(f"Keeping {len(self.representatives)} representatives for matching")

    def load_comments_by_size(self, match_tolerance: int = 0):
        """
        Load comments grouped by n-gram count, excluding already-found duplicates.

        Args:
            match_tolerance: How much n-gram count can differ (0 = exact match)

        Returns:
            Dictionary mapping n-gram count to list of (comment_id, ngram_set) tuples
        """
        logger.info(f"Loading unprocessed comments with match tolerance ±{match_tolerance}...")

        # The exclusion set is ONE array parameter, unnested for a hashed
        # anti-join, so the set has no limit on its size.
        if self.excluded_comments:
            exclusion_sql = "AND c.comment_id NOT IN (SELECT value FROM json_each(?))"
            exclusion_params = [json.dumps(list(self.excluded_comments))]
        else:
            exclusion_sql = ""
            exclusion_params = []

        # Get all non-excluded comments with their n-grams. The weight is the
        # text's exact-class size: the population is one original per class,
        # and the most-copied text in a bucket should lead its group.
        query = f"""
            SELECT c.comment_id, json_group_array(c.ngram_id) as ngram_ids,
                   COUNT(*) as ngram_count,
                   COALESCE(max(d.duplicate_group_size), 1) as weight
            FROM {{analysis}}.comment_long_ngrams c
            LEFT JOIN {{analysis}}.comment_dedup d ON d.comment_id = c.comment_id
            WHERE 1=1 {exclusion_sql}
            GROUP BY c.comment_id
            ORDER BY ngram_count, c.comment_id
        """

        self._cur().execute(self.ctx.render_sql(query), exclusion_params)

        # Group by n-gram count
        comments_by_size = defaultdict(list)
        total = 0
        representatives_included = 0
        representative_ids = set(self.representatives.values())

        for row in self._cur():
            comment_id = row['comment_id']
            ngram_ids = set(json.loads(row['ngram_ids']))
            ngram_count = row['ngram_count']

            # Check if this is a representative
            if comment_id in representative_ids:
                representatives_included += 1

            comments_by_size[ngram_count].append((comment_id, ngram_ids, row['weight']))
            total += 1

            if total % 10000 == 0:
                logger.info(f"Loaded {total:,} comments...")

        logger.info(f"Loaded {total:,} unprocessed comments in {len(comments_by_size)} size groups")
        logger.info(f"Including {representatives_included} representatives from existing groups")

        # If match_tolerance > 0, merge adjacent size groups
        if match_tolerance > 0:
            merged = defaultdict(list)
            processed = set()

            for size in sorted(comments_by_size.keys()):
                if size in processed:
                    continue

                # Create a merged group for this size range
                group_key = size
                merged[group_key].extend(comments_by_size[size])
                processed.add(size)

                # Add adjacent sizes within tolerance
                for offset in range(1, match_tolerance + 1):
                    for neighbor in [size - offset, size + offset]:
                        if neighbor in comments_by_size and neighbor not in processed:
                            merged[group_key].extend(comments_by_size[neighbor])
                            processed.add(neighbor)

            logger.info(f"Merged into {len(merged)} groups with tolerance ±{match_tolerance}")
            return merged

        return comments_by_size

    def find_duplicates_in_group(self, comments: List[Tuple[str, Set[int], int]],
                                similarity_threshold: float = 0.85) -> List[Tuple[str, Set[str]]]:
        """
        Group the comments of one size bucket by leader assignment
        (assign_leaders), representatives of stored groups leading first.
        Returns [(leader_id, members)].
        """
        if len(comments) <= 1:
            return [(c[0], {c[0]}) for c in comments]

        rep_ids = set(self.representatives.values())
        num_reps = sum(1 for c in comments if c[0] in rep_ids)
        if num_reps > 0:
            logger.debug(f"Processing group with {len(comments)} comments ({num_reps} representatives)")

        t0 = time.time()
        groups = assign_leaders(comments, similarity_threshold, seeded=rep_ids)

        # Log statistics for large groups
        if len(comments) > 100:
            logger.info(f"Size {len(comments[0][1])}: {len(comments)} comments → "
                       f"{len(groups)} groups in {time.time() - t0:.1f}s")

        return groups

    def find_all_duplicates(self, match_tolerance: int = 0,
                           similarity_threshold: float = 0.85,
                           on_bucket=None) -> Tuple[List[Tuple[str, Set[str]]], Dict]:
        """Find all duplicate groups incrementally. `on_bucket(groups)` is
        called with each size bucket's groups as soon as that bucket is done
        (main passes store_groups), so a crash costs the bucket in flight and
        nothing before it. Buckets are
        disjoint, so a bucket's groups are final when it finishes."""

        logger.info(f"Finding NEW duplicates with tolerance ±{match_tolerance} and threshold {similarity_threshold:.0%}")

        # Load existing groups first
        self.load_existing_groups()

        # Load unprocessed comments
        comments_by_size = self.load_comments_by_size(match_tolerance)

        # Process each size group
        all_groups = []
        stats = {
            'total_comments': 0,
            'new_groups': 0,
            'expanded_groups': 0,
            'representatives_matched': 0,
            'size_groups_processed': 0
        }

        sorted_sizes = sorted(comments_by_size.keys(),
                            key=lambda k: len(comments_by_size[k]),
                            reverse=True)

        for size in sorted_sizes:
            comments = comments_by_size[size]

            if len(comments) < 2:
                # Single comment
                all_groups.append((comments[0][0], {comments[0][0]}))
                continue

            if len(comments) > 100:
                logger.info(f"Processing {len(comments)} comments with ~{size} n-grams...")

            groups = self.find_duplicates_in_group(comments, similarity_threshold)
            if on_bucket is not None:
                on_bucket(groups)

            # Check if any groups contain representatives (meaning they expanded existing groups)
            rep_ids = set(self.representatives.values())
            for _leader, members in groups:
                if any(cid in rep_ids for cid in members):
                    stats['expanded_groups'] += 1
                    # Count how many representatives matched
                    stats['representatives_matched'] += sum(1 for cid in members if cid in rep_ids)
                else:
                    stats['new_groups'] += 1

            all_groups.extend(groups)
            stats['total_comments'] += len(comments)
            stats['size_groups_processed'] += 1

        # Sort groups by size
        all_groups.sort(key=lambda g: len(g[1]), reverse=True)

        logger.info(f"Found {len(all_groups)} total groups")
        logger.info(f"  - {stats['new_groups']} completely new groups")
        logger.info(f"  - {stats['expanded_groups']} groups that expand existing ones")
        logger.info(f"  - {stats['representatives_matched']} representatives matched new comments")

        return all_groups, stats

    def rebuild(self):
        """Empty the stored groups so a full run starts clean: they were
        computed on the n-grams as they stood, and a re-extraction changes
        every n-gram id. duplicate_detection_runs is kept as provenance."""
        self._cur().execute(self.ctx.render_sql("DELETE FROM {analysis}.duplicate_group_members"))
        self._cur().execute(self.ctx.render_sql("DELETE FROM {analysis}.duplicate_groups"))
        self._conn().commit()
        logger.info("Rebuild: stored duplicate groups emptied")

    def store_groups(self, groups: List[Tuple[str, Set[str]]], min_group_size: int = 40):
        """Store one batch of groups (a size bucket's, or a whole run's),
        appending to existing groups, and commit. Called per bucket as the
        run goes, so nothing waits for the end.

        Args:
            min_group_size: Minimum size for NEW groups to be considered significant.
                           Existing groups are always expanded regardless of size.
        """
        # Don't clear existing results!
        # Instead, append new findings

        rep_ids = set(self.representatives.values())
        new_groups_stored = 0
        expanded_groups_stored = 0
        skipped_small_groups = 0
        members_added_to_existing = 0

        for leader, group in groups:
            if len(group) < 2:
                continue

            # Check if this group contains a representative
            matching_reps = [cid for cid in group if cid in rep_ids]

            if matching_reps:
                # This expands an existing group: the LEADER's. Stored
                # representatives are seeded first in assign_leaders, so a
                # cluster holding any representative is led by one. The
                # cluster's new comments join that one group. Added to EVERY
                # group whose representative is in the cluster, two
                # representatives near each other would put each new comment
                # into two groups, and the family build downstream would find
                # texts in two cores. The other
                # representatives keep their own groups; two existing groups
                # being near each other is not a reason to move their members.
                group_id = expansion_target(leader, matching_reps, self.representatives)
                if group_id is not None:
                    new_members = [cid for cid in group if cid not in rep_ids]
                    for comment_id in new_members:
                        self._cur().execute(
                            self.ctx.render_sql("""
                            INSERT INTO {analysis}.duplicate_group_members
                            (group_id, comment_id, is_representative)
                            VALUES (?, ?, FALSE)
                            ON CONFLICT DO NOTHING
                            """),
                            (group_id, comment_id)
                        )

                    # Update group size
                    self._cur().execute(
                        self.ctx.render_sql("""
                        UPDATE {analysis}.duplicate_groups
                        SET group_size = (
                            SELECT COUNT(*) FROM {analysis}.duplicate_group_members
                            WHERE group_id = ?
                        )
                        WHERE group_id = ?
                        """),
                        (group_id, group_id)
                    )
                    expanded_groups_stored += 1
                    members_added_to_existing += len(new_members)
            else:
                # Completely new group - only store if large enough
                if len(group) < min_group_size:
                    skipped_small_groups += 1
                    continue

                sorted_ids = sorted(group)
                group_hash = hashlib.md5('_'.join(sorted_ids).encode()).hexdigest()

                # Insert new group
                self._cur().execute(
                    self.ctx.render_sql("""
                    INSERT INTO {analysis}.duplicate_groups (group_hash, group_size)
                    VALUES (?, ?)
                    RETURNING group_id
                    """),
                    (group_hash, len(group))
                )
                group_id = _one(self._cur())['group_id']

                # Insert members; the leader is the representative
                for comment_id in sorted_ids:
                    is_representative = (comment_id == leader)
                    self._cur().execute(
                        self.ctx.render_sql("""
                        INSERT INTO {analysis}.duplicate_group_members
                        (group_id, comment_id, is_representative)
                        VALUES (?, ?, ?)
                        """),
                        (group_id, comment_id, is_representative)
                    )
                new_groups_stored += 1

        self._conn().commit()
        self.stored['expanded'] += expanded_groups_stored
        self.stored['members_added'] += members_added_to_existing
        self.stored['new'] += new_groups_stored
        self.stored['skipped'] += skipped_small_groups
        return new_groups_stored, expanded_groups_stored, skipped_small_groups

    def log_run(self, groups: List[Tuple[str, Set[str]]], stats: Dict,
                method: str = 'incremental', execution_time: float = 0,
                min_group_size: int = 40):
        """The run's provenance row and the storage summary, after every
        bucket has been stored."""
        self._cur().execute(
            self.ctx.render_sql("""
            INSERT INTO {analysis}.duplicate_detection_runs
            (detection_method, total_comments_analyzed, total_pairs_found,
             execution_time_seconds, parameters)
            VALUES (?, ?, ?, ?, ?)
            """),
            (
                method,
                stats['total_comments'],
                sum(len(g) * (len(g) - 1) // 2 for _l, g in groups if len(g) >= 2),
                execution_time,
                json.dumps(stats)
            )
        )
        self._conn().commit()
        logger.info(f"Storage summary (min new group size: {min_group_size}):")
        logger.info(f"  - Expanded {self.stored['expanded']} existing groups with"
                    f" {self.stored['members_added']} new members")
        logger.info(f"  - Created {self.stored['new']} new groups (≥{min_group_size} members)")
        logger.info(f"  - Skipped {self.stored['skipped']} small groups (<{min_group_size} members)")


def main():
    parser = argparse.ArgumentParser(description='Incremental duplicate detection')
    add_project_argument(parser)
    parser.add_argument('--match', type=int, default=1,
                        help='N-gram count difference tolerance (0=exact, 1=±1, 2=±2, etc.)')
    parser.add_argument('--threshold', type=float, default=0.85,
                        help='Similarity threshold (0.0-1.0, default 0.85)')
    parser.add_argument('--min-group-size', type=int, default=40,
                        help='Minimum size for new groups to be stored (default 40)')
    parser.add_argument('--no-store', action='store_true',
                        help='Skip storing results to database')
    parser.add_argument('--rebuild', action='store_true',
                        help='Empty the stored groups first (after a re-extraction) and'
                             ' group the whole population')

    args = parser.parse_args()

    ctx = context_from_args(args)

    detector = IncrementalDuplicateDetector(ctx)

    try:
        start_time = time.time()
        detector.connect()
        if args.rebuild:
            detector.rebuild()

        # Find duplicates incrementally, storing each size bucket's groups as
        # it finishes (unless --no-store).
        def store_bucket(groups):
            detector.store_groups(groups, min_group_size=args.min_group_size)
        on_bucket = None if args.no_store else store_bucket
        groups, stats = detector.find_all_duplicates(
            match_tolerance=args.match,
            similarity_threshold=args.threshold,
            on_bucket=on_bucket
        )

        execution_time = time.time() - start_time
        logger.info(f"Total execution time: {execution_time:.2f} seconds")

        if not args.no_store:
            detector.log_run(groups, stats,
                             method=f'incremental_{args.match}',
                             execution_time=execution_time,
                             min_group_size=args.min_group_size)

        # Print summary
        print("\n" + "=" * 60)
        print("INCREMENTAL DUPLICATE DETECTION SUMMARY")
        print("=" * 60)
        print(f"Match tolerance: ±{args.match} n-grams")
        print(f"Similarity threshold: {args.threshold:.0%}")
        print(f"Total NEW comments processed: {stats['total_comments']:,}")
        print(f"Groups found: {len(groups):,}")
        print(f"  - Completely new groups: {stats['new_groups']}")
        print(f"  - Groups expanding existing ones: {stats['expanded_groups']}")
        print(f"  - Representatives that matched: {stats['representatives_matched']}")

        if groups:
            print(f"\nLargest group: {len(groups[0][1]):,} members (leader {groups[0][0]})")

            # Show size distribution, every size
            print("\nGroup size distribution:")
            size_counts = defaultdict(int)
            for _leader, members in groups:
                size_counts[len(members)] += 1

            for size in sorted(size_counts.keys(), reverse=True):
                print(f"  {size:5d} members: {size_counts[size]:5d} groups")

        print(f"\nExecution time: {execution_time:.2f} seconds")

    except Exception as e:
        logger.error(f"Detection failed: {e}")
        raise
    finally:
        detector.close()


if __name__ == "__main__":
    main()