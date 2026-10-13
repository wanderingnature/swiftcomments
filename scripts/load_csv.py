#!/usr/bin/env python3
"""Load the regulations.gov bulk download of the docket into data/roadless.sqlite:
one `comment` row per record, blanks and withdrawn rows kept and
flagged, and one `attachment_file` row per rendition of each attachment.

    uv run python scripts/load_csv.py csv/mv4-z8fw-q5jx.csv

The export is one CSV with 60 columns; a comment's text spans lines, which the csv
module handles. The columns read: Document ID (the comment_id), Comment, Posted
Date, Received Date, Is Withdrawn? (true/false), Reason Withdrawn, Title, Tracking
Number, Government Agency, Attachment Files (the URLs, comma-separated:
https://downloads.regulations.gov/<comment_id>/attachment_<n>.<ext>). Every record
must be a Public Submission of docket FS-2025-0001; any other stops the load.

Loads into empty tables only: a second load is a `make schema --force` away.
Prints what it is about to do, a line every 50,000 records, and the row counts it
wrote.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared import db  # noqa: E402

DOCKET = "FS-2025-0001"
DOCUMENT_TYPE = "Public Submission"
URL_RE = re.compile(r"^https://downloads\.regulations\.gov/([^/]+)/attachment_(\d+)\.([A-Za-z0-9]+)$")
BATCH = 5000
PROGRESS = 50000


def records(path: Path):
    csv.field_size_limit(1 << 30)
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for n, row in enumerate(reader, 1):
            if row["Docket ID"] != DOCKET or row["Document Type"] != DOCUMENT_TYPE:
                raise SystemExit(
                    f"record {n} ({row['Document ID']}) is {row['Docket ID']!r} / "
                    f"{row['Document Type']!r}; the loader expects {DOCKET!r} / {DOCUMENT_TYPE!r}.")
            withdrawn = row["Is Withdrawn?"]
            if withdrawn not in ("true", "false"):
                raise SystemExit(f"record {n}: Is Withdrawn? is {withdrawn!r}, not true or false.")
            yield row, withdrawn == "true"


def attachment_rows(comment_id: str, field: str):
    for url in filter(None, field.split(",")):
        m = URL_RE.match(url)
        if not m or m.group(1) != comment_id:
            raise SystemExit(f"{comment_id}: attachment URL not in the expected form: {url!r}")
        yield comment_id, int(m.group(2)), m.group(3).lower(), url


def load(conn, path: Path) -> tuple[int, int, int, int]:
    """Load `path`; return (comments, with text, withdrawn, attachment files)."""
    for table in ("comment", "attachment_file"):
        if conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]:
            raise SystemExit(f"{table} is not empty; run `make schema --force` for a fresh file.")
    print(f"loading {path}: one comment row per record (blank and withdrawn rows kept and"
          f" flagged), one attachment_file row per attachment URL; committed at the end;"
          f" a line every {PROGRESS:,} records", flush=True)
    comments, files = [], []
    n_comments = n_text = n_withdrawn = n_files = 0
    for row, withdrawn in records(path):
        comments.append((row["Document ID"], row["Comment"], row["Posted Date"] or None,
                         row["Received Date"] or None, int(withdrawn),
                         row["Reason Withdrawn"] or None, row["Title"] or None,
                         row["Tracking Number"] or None, row["Government Agency"] or None))
        files.extend(attachment_rows(row["Document ID"], row["Attachment Files"]))
        n_comments += 1
        n_text += bool(row["Comment"])
        n_withdrawn += withdrawn
        if n_comments % PROGRESS == 0:
            print(f"  {n_comments:,} records read", flush=True)
        if len(comments) >= BATCH:
            _flush(conn, comments, files)
            n_files += len(files)
            comments, files = [], []
    _flush(conn, comments, files)
    n_files += len(files)
    print(f"  {n_comments:,} records read; committing", flush=True)
    conn.commit()
    return n_comments, n_text, n_withdrawn, n_files


def _flush(conn, comments, files) -> None:
    conn.executemany(
        "INSERT INTO comment (comment_id, comment_text, posted_date, received_date, withdrawn,"
        " withdrawn_reason, title, tracking_number, government_agency)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", comments)
    conn.executemany(
        "INSERT INTO attachment_file (comment_id, ordinal, format, url) VALUES (?, ?, ?, ?)", files)


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("csv", type=Path, help="the bulk download, e.g. csv/mv4-z8fw-q5jx.csv")
    args = parser.parse_args()
    if not args.csv.exists():
        raise SystemExit(f"{args.csv} does not exist.")
    conn = db.connect()
    n_comments, n_text, n_withdrawn, n_files = load(conn, args.csv)
    conn.close()
    print(f"comment: {n_comments:,} rows ({n_text:,} with text, {n_withdrawn} withdrawn)")
    print(f"attachment_file: {n_files:,} rows")


if __name__ == "__main__":
    main()
