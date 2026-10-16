"""One JSON file per comment, the same shape from both substance readings, so
the two can be set side by side. Written by `make score-model-compare`
(scripts/score_model_compare.py), from the model's reading
(json_record in scripts/substance/score_comments.py) and the rules' reading
(json_record in scripts/model_free/run.py).

    {
      "comment_id": "FS-2025-0001-224412",
      "scorer":     "model" | "rules",
      "instrument": "v3" | "rules-3",
      "model":      the model name for the model's reading, null for the rules',
      "levels":     {"PLACE": 0..3, "STAND", "DOC", "GAP", "EVID", "ASK", "ALT", "LAW"},
      "strength":   the sum of the eight,
      "gate":       true | false,
      "gate_basis": the dimensions that opened it (as each scorer records them),
      "band":       "minimal" | "marginal" | "developed" | "strong",
      "a_level":    "A0".."A3" | null (the model's reading gets its level from make rate),
      "evidence":   a list, one entry per thing the scorer found: the model's
                    spans, or the rules' hits (dimension, grade, rule, match, start, end)
    }
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DIMS = ("PLACE", "STAND", "DOC", "GAP", "EVID", "ASK", "ALT", "LAW")
KEYS = ("comment_id", "scorer", "instrument", "model", "levels", "strength", "gate",
        "gate_basis", "band", "a_level", "evidence")
BANDS = ("minimal", "marginal", "developed", "strong")


def check(record: dict) -> dict:
    """The record, or a ValueError naming the first key that is missing or wrong."""
    missing = [k for k in KEYS if k not in record]
    if missing:
        raise ValueError(f"score record for {record.get('comment_id')!r} lacks {', '.join(missing)}")
    extra = [k for k in record if k not in KEYS]
    if extra:
        raise ValueError(f"score record for {record['comment_id']!r} has unknown keys {', '.join(extra)}")
    if record["scorer"] not in ("model", "rules"):
        raise ValueError(f"{record['comment_id']}: scorer must be model or rules, not {record['scorer']!r}")
    levels = record["levels"]
    if set(levels) != set(DIMS):
        raise ValueError(f"{record['comment_id']}: levels must hold exactly {', '.join(DIMS)}")
    for d in DIMS:
        if not isinstance(levels[d], int) or not 0 <= levels[d] <= 3:
            raise ValueError(f"{record['comment_id']}: {d} must be an integer 0 to 3, not {levels[d]!r}")
    if record["strength"] != sum(levels[d] for d in DIMS):
        raise ValueError(f"{record['comment_id']}: strength {record['strength']} is not the sum of the levels")
    if record["band"] not in BANDS:
        raise ValueError(f"{record['comment_id']}: band {record['band']!r}")
    if record["a_level"] is not None and record["a_level"] not in ("A0", "A1", "A2", "A3"):
        raise ValueError(f"{record['comment_id']}: a_level {record['a_level']!r}")
    if not isinstance(record["gate"], bool) or not isinstance(record["evidence"], list):
        raise ValueError(f"{record['comment_id']}: gate must be a boolean and evidence a list")
    return record


def write(directory: Path, record: dict) -> Path:
    """Write the checked record as <directory>/<comment_id>.json, replacing a
    file from an earlier run of the same scorer."""
    check(record)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{record['comment_id']}.json"
    path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_dir(directory: Path) -> dict[str, dict]:
    """Every record in a folder, by comment id; a file that fails the check
    stops the read with its name."""
    directory = Path(directory)
    if not directory.is_dir():
        raise SystemExit(f"{directory}: not a folder of score files")
    out: dict[str, dict] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            rec = check(json.loads(path.read_text(encoding="utf-8")))
        except ValueError as exc:
            raise SystemExit(f"{path}: {exc}") from None
        out[rec["comment_id"]] = rec
    if not out:
        raise SystemExit(f"{directory}: no score files")
    return out


def gate_dimensions(rec: dict) -> list[str]:
    """The dimensions that opened the gate: the model records names, the rules
    records {dimension, unit_id}."""
    return [b["dimension"] if isinstance(b, dict) else str(b) for b in rec["gate_basis"]]


def evidence_by_dimension(rec: dict) -> tuple[dict[str, list[str]], list[str]]:
    """The record's evidence as readable lines, per dimension, and the lines that
    belong to no dimension (the model's rationale, the rules' moves). A model
    line is its span in quotes and the grading rule; a rules line is the rule
    and the words it matched."""
    by = {d: [] for d in DIMS}
    other = []
    for e in rec["evidence"]:
        d = e.get("dimension")
        if "rule" in e:
            line = f'{e["rule"]}: "{e.get("match", "")}"'
        elif d == "rationale":
            other.append(f"rationale: {e.get('span')}")
            continue
        else:
            span = e.get("span")
            rules = ", ".join(r.get("rule", "") for r in e.get("rules") or [])
            line = (f'"{span}"' if span and span != "none" else "no span") + (f" ({rules})" if rules else "")
        if d in by:
            by[d].append(line)
        else:
            other.append(f"{d}: {line}")
    return by, other


def dimension_rows(a: dict[str, dict], b: dict[str, dict], labels=("A", "B")) -> list[dict]:
    """Per dimension over the comments both hold: how many agree, how many each
    side reads higher, each side's mean level."""
    both = sorted(set(a) & set(b))
    la, lb = labels
    rows = []
    for d in DIMS:
        same = sum(1 for c in both if a[c]["levels"][d] == b[c]["levels"][d])
        up = sum(1 for c in both if a[c]["levels"][d] > b[c]["levels"][d])
        rows.append({"dimension": d, "same": same, f"{la} higher": up, f"{lb} higher": len(both) - same - up,
                     f"{la} mean": round(sum(a[c]["levels"][d] for c in both) / len(both), 2),
                     f"{lb} mean": round(sum(b[c]["levels"][d] for c in both) / len(both), 2)})
    return rows


def differing(a: dict[str, dict], b: dict[str, dict]) -> tuple[list[str], list[str]]:
    """The comments both hold whose gate differs, then those whose gate agrees
    and a level does not."""
    both = sorted(set(a) & set(b))
    gate = [c for c in both if a[c]["gate"] != b[c]["gate"]]
    level = [c for c in both if a[c]["gate"] == b[c]["gate"]
             and any(a[c]["levels"][d] != b[c]["levels"][d] for d in DIMS)]
    return gate, level


def gate_text(rec: dict) -> str:
    dims = gate_dimensions(rec)
    if not rec["gate"]:
        return "closed"
    return "open (" + ", ".join(dims) + ")" if dims else "open"


def comment_rows(ra: dict, rb: dict, labels=("A", "B")) -> list[dict]:
    """One comment, dimension by dimension: each side's level and evidence, and
    whether the levels differ."""
    la, lb = labels
    ea, _ = evidence_by_dimension(ra)
    eb, _ = evidence_by_dimension(rb)
    return [{"dimension": d, "differs": "*" if ra["levels"][d] != rb["levels"][d] else "",
             la: ra["levels"][d], lb: rb["levels"][d],
             f"{la} evidence": "\n".join(ea[d]), f"{lb} evidence": "\n".join(eb[d])} for d in DIMS]


def compare(a: dict[str, dict], b: dict[str, dict], limit: int, out=None, labels=("A", "B")) -> int:
    """Two sets of records, by comment id, side by side on the comments both
    hold, as text: per dimension how many agree, which side reads higher and
    each side's mean; the gate, band and strength; then each comment where the
    gate differs, then each where the gate agrees and a level does not, all
    eight dimensions with each side's level and evidence, a differing level
    marked *, up to `limit` (0 for all). Printed to `out` (stdout when None).
    make score-model-compare prints it; the console's Compare page shows the
    same figures as tables."""
    out = sys.stdout if out is None else out
    la, lb = labels
    w = max(len(la), len(lb))

    def p(line=""):
        print(line, file=out)

    both = sorted(set(a) & set(b))
    for label, recs in ((la, a), (lb, b)):
        instruments = ", ".join(sorted({r["instrument"] for r in recs.values()}))
        models = ", ".join(sorted({r["model"] for r in recs.values() if r["model"]}))
        p(f"{label:<{w}}  {len(recs):,} comments, instrument {instruments}" + (f", model {models}" if models else ""))
    p(f"both read {len(both):,}; only {la} {len(set(a) - set(b)):,}; only {lb} {len(set(b) - set(a)):,}")
    if not both:
        return 1

    rows = dimension_rows(a, b, labels)
    cols = list(rows[0])
    widths = [max(len(c), *(len(str(r[c])) for r in rows)) for c in cols]
    p()
    p("  ".join(c.rjust(wd) if i else c.ljust(wd) for i, (c, wd) in enumerate(zip(cols, widths))))
    for r in rows:
        p("  ".join(str(r[c]).rjust(wd) if i else str(r[c]).ljust(wd) for i, (c, wd) in enumerate(zip(cols, widths))))
    same_all = sum(1 for c in both if all(a[c]["levels"][d] == b[c]["levels"][d] for d in DIMS))
    p(f"all eight the same on {same_all:,} of {len(both):,}")

    n = len(both)
    p()
    p(f"gate      same on {sum(1 for c in both if a[c]['gate'] == b[c]['gate']):,} of {n:,};"
      f" open: {la} {sum(1 for c in both if a[c]['gate']):,}, {lb} {sum(1 for c in both if b[c]['gate']):,},"
      f" both {sum(1 for c in both if a[c]['gate'] and b[c]['gate']):,}")
    p(f"band      same on {sum(1 for c in both if a[c]['band'] == b[c]['band']):,} of {n:,}")
    p(f"strength  same on {sum(1 for c in both if a[c]['strength'] == b[c]['strength']):,} of {n:,};"
      f" mean {la} {sum(a[c]['strength'] for c in both) / n:.2f}, {lb} {sum(b[c]['strength'] for c in both) / n:.2f};"
      f" mean absolute difference {sum(abs(a[c]['strength'] - b[c]['strength']) for c in both) / n:.2f}")
    rated = [c for c in both if a[c]["a_level"] is not None and b[c]["a_level"] is not None]
    if rated:
        p(f"level     same on {sum(1 for c in rated if a[c]['a_level'] == b[c]['a_level']):,} of {len(rated):,}"
          " rated on both sides")
    else:
        unrated = [lab for lab, recs in ((la, a), (lb, b)) if all(recs[c]["a_level"] is None for c in both)]
        p(f"level     not compared: {' and '.join(unrated)} carries no A level")

    gate, level = differing(a, b)
    listed = gate + level
    shown = listed if limit == 0 else listed[:limit]
    p()
    p(f"comments that differ: {len(gate):,} on the gate, {len(level):,} more on a level"
      + (f" (the first {len(shown)} listed)" if len(shown) < len(listed) else ""))
    for c in shown:
        ra, rb = a[c], b[c]
        p()
        p("=" * 78)
        p(c)
        p(f"  gate      {la}: {gate_text(ra)}    {lb}: {gate_text(rb)}")
        p(f"  strength  {la}: {ra['strength']}    {lb}: {rb['strength']}")
        p(f"  band      {la}: {ra['band']}    {lb}: {rb['band']}")
        for row in comment_rows(ra, rb, labels):
            p(f"  {row['differs'] or ' '} {row['dimension']:<5}  {la} {row[la]}  {lb} {row[lb]}")
            for side in (la, lb):
                lines = row[f"{side} evidence"].split("\n") if row[f"{side} evidence"] else ["-"]
                for i, line in enumerate(lines):
                    p(f"      {(side if i == 0 else ''):<{w}}  {line}")
        for side, rec in ((la, ra), (lb, rb)):
            for line in evidence_by_dimension(rec)[1]:
                p(f"  {side}: {line}")
    return 0
