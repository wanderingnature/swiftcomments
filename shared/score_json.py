"""One JSON file per comment, the same shape from both substance readings, so
the two can be set side by side (scripts/compare_scores.py). Written by
`make score-model JSON=dir` (the model's reading, scripts/substance/score_comments.py)
and `make score-model-free JSON=dir` (the rules' reading, scripts/model_free/run.py).

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
