"""
Database connection and utility functions — all project-scoped.

Every helper takes a ProjectContext as its first argument. SQL is written with
{analysis}/{src} tokens; DatabaseConnection.execute/execute_many and the cursor
helpers render them via ctx.render_sql() automatically, so a missed token is a
hard error, never a silent cross-project write.

The deduplication helpers only.
"""

import contextlib
import sqlite3
from typing import Generator, Any, Dict, List, Optional, Tuple

from shared import db
from shared.project_context import ProjectContext

from .logger import get_logger

logger = get_logger(__name__)


def _one(cur):
    """The single row a query must return. No row means the query is wrong."""
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("expected one row, got none")
    return row


class DatabaseConnection:
    """
    Project-scoped database connection manager with context support.
    """

    def __init__(self, ctx: ProjectContext):
        """
        Initialize database connection for one project.

        Args:
            ctx: ProjectContext (connection config + schema names)
        """
        self.ctx = ctx
        self._connection: Optional[db.Connection] = None

    def connect(self) -> db.Connection:
        """
        Create and return database connection.
        """
        if self._connection is None or self._connection.closed:
            try:
                self._connection = db.connect(**self.ctx.db_config)
                logger.info(f"Connected to database {self.ctx.db_config['path']}")
            except sqlite3.Error as e:
                logger.error(f"Failed to connect to database: {e}")
                raise

        return self._connection

    def close(self):
        """
        Close database connection.
        """
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("Database connection closed")

    def fetch(self, query: str, params: Optional[Tuple] = None) -> List[Tuple]:
        """Rows from a SELECT — always a list, never None.

        `execute(..., fetch=True)` is typed Optional because the same method also serves
        writes, so every caller that iterated or indexed its result was reading a possible
        None. This is the read path with its own honest signature.
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(self.ctx.render_sql(query), params or ())
            return list(cur.fetchall())

    def execute(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch: bool = False
    ) -> Optional[List[Tuple]]:
        """
        Execute a SQL query ({analysis}/{src} tokens rendered automatically).

        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results

        Returns:
            Query results if fetch=True
        """
        conn = self.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(self.ctx.render_sql(query), params or ())
                if fetch:
                    return cur.fetchall()
                conn.commit()
                return None
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Query execution failed: {e}")
            raise

    def execute_many(
        self,
        query: str,
        data: List[Tuple]
    ):
        """
        Execute query with multiple parameter sets (tokens rendered automatically).

        Args:
            query: SQL query string
            data: List of parameter tuples
        """
        conn = self.connect()
        try:
            with conn.cursor() as cur:
                cur.executemany(self.ctx.render_sql(query), data)
                conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Batch execution failed: {e}")
            raise

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


@contextlib.contextmanager
def get_db_connection(ctx: ProjectContext) -> Generator[db.Connection, None, None]:
    """
    Get database connection as context manager.

    Yields:
        Database connection
    """
    conn = None
    try:
        conn = db.connect(**ctx.db_config)
        yield conn
    finally:
        if conn:
            conn.close()


class _RenderingCursor:
    """Cursor wrapper that renders {analysis}/{src} tokens on execute."""

    def __init__(self, cursor: "db.Cursor", ctx: ProjectContext):
        self._cursor = cursor
        self._ctx = ctx

    def execute(self, query: str, params=None):
        return self._cursor.execute(self._ctx.render_sql(query), params or ())

    def executemany(self, query: str, params_seq):
        return self._cursor.executemany(self._ctx.render_sql(query), params_seq)

    def __getattr__(self, name):
        return getattr(self._cursor, name)

    def __iter__(self):
        return iter(self._cursor)


@contextlib.contextmanager
def get_db_cursor(
    ctx: ProjectContext,
    dict_cursor: bool = False
) -> Generator["_RenderingCursor", None, None]:
    """
    Get database cursor as context manager (token-rendering).

    Args:
        ctx: ProjectContext
        dict_cursor: Whether to use dict rows (every row is a sqlite3.Row, which
            reads by name and by index, so both cursors yield the same rows)

    Yields:
        Database cursor (renders {analysis}/{src} tokens on execute)
    """
    with get_db_connection(ctx) as conn:
        with conn.cursor() as cur:
            yield _RenderingCursor(cur, ctx)
            conn.commit()


def fetch_all_comments(
    ctx: ProjectContext,
    min_length: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Fetch all comments for deduplication processing.

    Args:
        ctx: ProjectContext
        min_length: Minimum comment length to include (optional)

    Returns:
        List of comment dictionaries with comment_id, comment_text, comment_length
    """
    query = """
        SELECT
            c.comment_id,
            c.comment_text,
            c.comment_length
        FROM {analysis}.v_source_comments c
        WHERE c.comment_text IS NOT NULL
    """

    params = {}
    if min_length:
        query += " AND c.comment_length >= :min_length"
        params["min_length"] = min_length

    query += " ORDER BY c.comment_id"

    with get_db_cursor(ctx, dict_cursor=True) as cur:
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        results = cur.fetchall()

    logger.info(f"Fetched {len(results)} comments for deduplication")
    return [dict(row) for row in results]


def update_comment_deduplication(ctx: ProjectContext, updates: List[Dict[str, Any]]) -> int:
    """
    Write deduplication results into the comment_dedup table.

    Unlike the single-project predecessor (which UPDATEd pre-existing
    comment_ids rows), comment_dedup is written BY deduplication: rows are
    upserted, one per comment.

    Args:
        ctx: ProjectContext
        updates: List of dictionaries containing:
            - comment_id
            - content_hash
            - content_hash_md5
            - is_original
            - original_comment_id
            - duplicate_group_size

    Returns:
        Number of records written
    """
    if not updates:
        return 0

    query = """
        INSERT INTO {analysis}.comment_dedup
            (comment_id, content_hash, content_hash_md5, is_original,
             original_comment_id, duplicate_group_size, hash_updated_at)
        VALUES
            (:comment_id, :content_hash, :content_hash_md5, :is_original,
             :original_comment_id, :duplicate_group_size, CURRENT_TIMESTAMP)
        ON CONFLICT (comment_id) DO UPDATE SET
            content_hash = EXCLUDED.content_hash,
            content_hash_md5 = EXCLUDED.content_hash_md5,
            is_original = EXCLUDED.is_original,
            original_comment_id = EXCLUDED.original_comment_id,
            duplicate_group_size = EXCLUDED.duplicate_group_size,
            hash_updated_at = CURRENT_TIMESTAMP
    """

    db_ = DatabaseConnection(ctx)
    conn = db_.connect()
    try:
        with conn.cursor() as cur:
            cur.executemany(ctx.render_sql(query), updates)
            conn.commit()
            records_updated = len(updates)
            logger.info(f"Successfully wrote {records_updated} deduplication records")
            return records_updated
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to write deduplication records: {e}")
        raise
    finally:
        db_.close()


def get_deduplication_stats(ctx: ProjectContext) -> Dict[str, Any]:
    """
    Get deduplication statistics from the database.

    Returns:
        Dictionary with deduplication statistics
    """
    query = """
        SELECT
            COUNT(*) as total_comments,
            SUM(CASE WHEN is_original = true THEN 1 ELSE 0 END) as unique_comments,
            SUM(CASE WHEN is_original = false THEN 1 ELSE 0 END) as duplicate_comments,
            COUNT(DISTINCT content_hash) as distinct_hashes,
            MAX(duplicate_group_size) as largest_duplicate_group,
            100.0 * SUM(CASE WHEN is_original = false THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) as duplicate_percentage
        FROM {analysis}.comment_dedup
        WHERE content_hash IS NOT NULL
    """

    with get_db_cursor(ctx, dict_cursor=True) as cur:
        cur.execute(query)
        result = _one(cur)
        if result:
            return dict(result)
        return {}


def get_top_duplicates(ctx: ProjectContext, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get the most duplicated comments.

    Args:
        ctx: ProjectContext
        limit: Number of top duplicates to return

    Returns:
        List of dictionaries with duplicate information
    """
    query = """
        SELECT
            d.content_hash,
            d.content_hash_md5,
            d.duplicate_group_size,
            MIN(d.comment_id) as sample_comment_id,
            substr(c.comment_text, 1, 200) as comment_preview,
            c.comment_length
        FROM {analysis}.comment_dedup d
        INNER JOIN {analysis}.v_source_comments c ON d.comment_id = c.comment_id
        WHERE d.is_original = true
          AND d.duplicate_group_size > 1
        GROUP BY d.content_hash, d.content_hash_md5, d.duplicate_group_size, c.comment_text, c.comment_length
        ORDER BY d.duplicate_group_size DESC
        LIMIT :limit
    """

    with get_db_cursor(ctx, dict_cursor=True) as cur:
        cur.execute(query, {"limit": limit})
        results = cur.fetchall()
        return [dict(row) for row in results]
