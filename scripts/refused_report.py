#!/usr/bin/env python3
"""The comments a provider refused in a stance run, as a Markdown document: every
group whose latest call in the run came back with error kind `refused`, with the
provider's message, the comment id, how many comments the group stands for, the
text's length and the text itself, in full, so the refusals can be read against
what was sent. Reads the file only. New (docs/model-server.md, "Refusals").

    uv run python scripts/refused_report.py --run reclass_20261013_234102 --out docs/refused-reclass_20261013_234102.md
    make stance-refused RUN=reclass_20261013_234102
"""
import argparse
import sys
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from shared import db  # noqa: E402


def report(conn, run_id):
    """The document's text for `run_id`, or a SystemExit when the run refused nothing."""
    run = conn.execute("SELECT model_name, run_timestamp FROM classification_runs"
                       " WHERE strftime('%Y%m%d_%H%M%S', run_timestamp) = ?",
                       (run_id.replace("reclass_", ""),)).fetchone()
    if run is None:
        raise SystemExit(f"no stance run {run_id}")
    rows = conn.execute(
        "SELECT i.comment_id, i.group_id, i.attempt, i.error_detail, g.size,"
        "       length(c.comment_text) AS chars, c.comment_text"
        " FROM ("
        "   SELECT comment_id, group_id, attempt, error_detail, error_kind,"
        "          row_number() OVER (PARTITION BY group_id ORDER BY attempt DESC) AS rn"
        "   FROM classification_run_items WHERE run_id = ?) i"
        " JOIN comment_group g USING (group_id)"
        " JOIN comment c ON c.comment_id = i.comment_id"
        " WHERE i.rn = 1 AND i.error_kind = 'refused'"
        " ORDER BY i.group_id", (run_id,)).fetchall()
    if not rows:
        raise SystemExit(f"{run_id} has no group refused by the provider")
    messages = sorted({(r["error_detail"] or "").strip() for r in rows})
    total_members = sum(r["size"] for r in rows)
    out = [f"# Comments the provider refused in stance run {run_id}", "",
           f"Model `{run['model_name']}`, run started {run['run_timestamp']}; this document"
           f" written {date.today().isoformat()} by `scripts/refused_report.py`.", "",
           f"{len(rows):,} groups, standing for {total_members:,} comments, got no stance from"
           " this run: the provider's content inspection refused the text before the model"
           " read it, with this message:", ""]
    for m in messages:
        out.append(f"> {m}")
    out += ["", "Each entry is the group's canonical comment as sent, in full. A group's members"
            " carry the same text or share it, so the whole group is unclassified under this run.",
            "", "| comment | group | comments in the group | characters | attempts |", "|---|---:|---:|---:|---:|"]
    for r in rows:
        out.append(f"| {r['comment_id']} | {r['group_id']} | {r['size']:,} | {r['chars']:,} | {r['attempt']} |")
    out += ["", "## The texts", ""]
    for r in rows:
        out += [f"### {r['comment_id']} (group {r['group_id']}, {r['size']:,} comment(s), {r['chars']:,} characters)", ""]
        out += ["> " + line for line in (r["comment_text"] or "").splitlines()] or [">"]
        out.append("")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--run", required=True, metavar="RUN_ID", help="the stance run")
    ap.add_argument("--out", metavar="FILE", help="write the document here (default: stdout)")
    args = ap.parse_args(argv)
    conn = db.connect(db.DB_PATH)
    conn.execute("PRAGMA query_only = 1")
    text = report(conn, args.run)
    conn.close()
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        n = text.count("\n### ")
        print(f"{args.out}: {n:,} refused group(s), {len(text.encode('utf-8')) / 1e3:,.0f} kB")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
