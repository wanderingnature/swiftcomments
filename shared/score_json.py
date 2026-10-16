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


def describe(records: dict[str, dict]) -> str:
    scorers = sorted({r["scorer"] for r in records.values()})
    instruments = sorted({r["instrument"] for r in records.values()})
    return f"{len(records):,} comments; scorer {', '.join(scorers)}; instrument {', '.join(instruments)}"


def evidence_lines(rec: dict) -> list[str]:
    out = []
    for e in rec["evidence"]:
        if "rule" in e:
            out.append(f"    {e.get('dimension', '?')} {e.get('grade', '?')} {e['rule']}: {e.get('match', '')!s}")
        else:
            out.append("    " + ", ".join(f"{k}={v!s}" for k, v in e.items()))
    return out


def compare(a: dict[str, dict], b: dict[str, dict], limit: int, out=None) -> int:
    """Two sets of records, by comment id, side by side on the comments both
    hold: per dimension how many agree and which side reads higher; the gate,
    band, strength and level agreement; then each comment where the gate
    differs, then each where the gate agrees and a level does not, with both
    sides' levels and evidence, up to `limit` (0 for all).
    Printed to `out` (stdout when None). make score-model-compare prints it and
    the console's Compare page shows it."""
    out = sys.stdout if out is None else out
    both = sorted(set(a) & set(b))
    print(f"A: {describe(a)}", file=out)
    print(f"B: {describe(b)}", file=out)
    print(f"in both: {len(both):,}; only in A: {len(set(a) - set(b)):,}; only in B: {len(set(b) - set(a)):,}",
          file=out)
    if not both:
        return 1
    print("\nper dimension: same level, A higher, B higher", file=out)
    for d in DIMS:
        same = sum(1 for c in both if a[c]["levels"][d] == b[c]["levels"][d])
        up = sum(1 for c in both if a[c]["levels"][d] > b[c]["levels"][d])
        print(f"  {d:5s}  {same:7,}  {up:7,}  {len(both) - same - up:7,}", file=out)
    same_all = sum(1 for c in both if all(a[c]["levels"][d] == b[c]["levels"][d] for d in DIMS))
    print(f"identical on all eight: {same_all:,} of {len(both):,}", file=out)
    gate_same = sum(1 for c in both if a[c]["gate"] == b[c]["gate"])
    a_open = sum(1 for c in both if a[c]["gate"])
    b_open = sum(1 for c in both if b[c]["gate"])
    print(f"\ngate: same on {gate_same:,} of {len(both):,}; open in A {a_open:,}, in B {b_open:,},"
          f" in both {sum(1 for c in both if a[c]['gate'] and b[c]['gate']):,}", file=out)
    print(f"band: same on {sum(1 for c in both if a[c]['band'] == b[c]['band']):,}", file=out)
    rated = [c for c in both if a[c]["a_level"] is not None and b[c]["a_level"] is not None]
    if rated:
        print(f"answerability level: same on"
              f" {sum(1 for c in rated if a[c]['a_level'] == b[c]['a_level']):,} of {len(rated):,} rated on both sides",
              file=out)
    else:
        print("answerability level: not rated on both sides", file=out)
    diff = sum(abs(a[c]["strength"] - b[c]["strength"]) for c in both)
    print(f"strength: same on {sum(1 for c in both if a[c]['strength'] == b[c]['strength']):,};"
          f" mean absolute difference {diff / len(both):.2f}", file=out)

    disagreements = [c for c in both if a[c]["gate"] != b[c]["gate"]]
    changed = [c for c in both if a[c]["gate"] == b[c]["gate"]
               and any(a[c]["levels"][d] != b[c]["levels"][d] for d in DIMS)]
    listed = disagreements + changed
    shown = listed if limit == 0 else listed[:limit]
    print(f"\ngate disagreements: {len(disagreements):,}; the same gate with a level that differs:"
          f" {len(changed):,}" + (f" (the first {len(shown)} listed)" if len(shown) < len(listed) else ""),
          file=out)
    for c in shown:
        print(f"\n{c}: A gate={a[c]['gate']} basis={a[c]['gate_basis']} | B gate={b[c]['gate']} basis={b[c]['gate_basis']}",
              file=out)
        print("  A " + " ".join(f"{d} {a[c]['levels'][d]}" for d in DIMS), file=out)
        for line in evidence_lines(a[c]):
            print(line, file=out)
        print("  B " + " ".join(f"{d} {b[c]['levels'][d]}" for d in DIMS), file=out)
        for line in evidence_lines(b[c]):
            print(line, file=out)
    return 0
