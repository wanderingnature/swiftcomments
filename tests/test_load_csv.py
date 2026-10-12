"""The loader over a twenty-record cut of the bulk download (tests/fixtures/
bulk_cut.csv): a withdrawn row, a blank row, a multi-line comment, a comment with
twelve attachment renditions. Real code, a real temporary SQLite file through
shared/db.py (plan 5.3).

    uv run pytest tests/test_load_csv.py
"""
import csv
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from scripts import load_csv  # noqa: E402
from shared import db  # noqa: E402

FIXTURE = _REPO / "tests" / "fixtures" / "bulk_cut.csv"


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "roadless.sqlite", create=True)
    c.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    yield c
    c.close()


@pytest.fixture
def loaded(conn):
    counts = load_csv.load(conn, FIXTURE)
    return conn, counts


def test_counts_are_the_cut(loaded):
    _conn, (comments, with_text, withdrawn, files) = loaded
    assert (comments, with_text, withdrawn, files) == (20, 16, 2, 14)


def test_every_record_is_a_row_and_the_view_excludes_blank_text(loaded):
    conn, _ = loaded
    assert conn.execute("SELECT count(*) FROM comment").fetchone()[0] == 20
    assert conn.execute("SELECT count(*) FROM v_source_comments").fetchone()[0] == 16
    blank = [r["comment_id"] for r in conn.execute(
        "SELECT comment_id FROM comment WHERE comment_text = '' ORDER BY 1")]
    assert blank == ["FS-2025-0001-282826", "FS-2025-0001-345703",
                     "FS-2025-0001-393788", "FS-2025-0001-573775"]


def test_withdrawn_rows_are_flagged_with_their_reason(loaded):
    conn, _ = loaded
    rows = {r["comment_id"]: (r["withdrawn"], r["withdrawn_reason"]) for r in conn.execute(
        "SELECT comment_id, withdrawn, withdrawn_reason FROM comment WHERE withdrawn = 1")}
    assert rows == {
        "FS-2025-0001-345703": (1, "Author submitted an amended version of the letter on 9/15."),
        "FS-2025-0001-573775": (1, "Protecting private information."),
    }
    blank_not_withdrawn = conn.execute(
        "SELECT withdrawn, withdrawn_reason FROM comment WHERE comment_id = 'FS-2025-0001-282826'").fetchone()
    assert tuple(blank_not_withdrawn) == (0, None)


def test_a_multi_line_comment_keeps_its_lines(loaded):
    conn, _ = loaded
    text = conn.execute(
        "SELECT comment_text FROM comment WHERE comment_id = 'FS-2025-0001-223881'").fetchone()[0]
    assert "\n" in text
    with open(FIXTURE, newline="", encoding="utf-8") as fh:
        raw = next(r["Comment"] for r in csv.DictReader(fh) if r["Document ID"] == "FS-2025-0001-223881")
    assert text == raw


def test_dates_and_fields_come_through_as_the_export_gives_them(loaded):
    conn, _ = loaded
    r = conn.execute("SELECT * FROM comment WHERE comment_id = 'FS-2025-0001-223870'").fetchone()
    assert r["posted_date"] == "2026-08-20T04:00Z"
    assert r["received_date"] == "2026-08-20T04:00Z"
    assert r["title"] == "Comment on FR Doc # 2026-16965"
    assert r["tracking_number"] == "mt1-igxf-lnur"
    assert r["government_agency"] is None
    v = conn.execute("SELECT comment_length FROM v_source_comments WHERE comment_id = 'FS-2025-0001-223870'").fetchone()
    assert v["comment_length"] == len(r["comment_text"])


def test_one_attachment_file_row_per_rendition(loaded):
    conn, _ = loaded
    pair = conn.execute(
        "SELECT ordinal, format, url FROM attachment_file WHERE comment_id = 'FS-2025-0001-223888'"
        " ORDER BY ordinal, format").fetchall()
    assert [(r["ordinal"], r["format"]) for r in pair] == [(1, "docx"), (1, "pdf")]
    assert pair[1]["url"] == "https://downloads.regulations.gov/FS-2025-0001-223888/attachment_1.pdf"
    twelve = conn.execute(
        "SELECT ordinal, format FROM attachment_file WHERE comment_id = 'FS-2025-0001-224906'"
        " ORDER BY ordinal, format").fetchall()
    assert [(r["ordinal"], r["format"]) for r in twelve] == [
        (n, f) for n in range(1, 7) for f in ("jpg", "pdf")]
    assert conn.execute("SELECT count(*) FROM attachment_file").fetchone()[0] == 14
    assert conn.execute("SELECT count(DISTINCT comment_id) FROM attachment_file").fetchone()[0] == 2


def test_a_second_load_is_refused(loaded):
    conn, _ = loaded
    with pytest.raises(SystemExit, match="not empty"):
        load_csv.load(conn, FIXTURE)


def test_a_record_of_another_docket_stops_the_load(conn, tmp_path):
    with open(FIXTURE, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames
        row = next(reader)
    row["Docket ID"] = "FS-2025-0002"
    bad = tmp_path / "bad.csv"
    with open(bad, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerow(row)
    with pytest.raises(SystemExit, match="FS-2025-0002"):
        load_csv.load(conn, bad)
    assert conn.execute("SELECT count(*) FROM comment").fetchone()[0] == 0


def test_an_attachment_url_of_another_shape_stops_the_load(conn, tmp_path):
    with open(FIXTURE, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames
        row = next(reader)
    row["Attachment Files"] = "https://example.org/FS-2025-0001-223870/attachment_1.pdf"
    bad = tmp_path / "bad.csv"
    with open(bad, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerow(row)
    with pytest.raises(SystemExit, match="attachment URL"):
        load_csv.load(conn, bad)
