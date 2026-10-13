"""Model-free substantive scoring, fully parallel to v3.

The method: docs/methods-scoring.md and docs/model-free-scoring.md.

This package imports nothing from scripts/substance/ or shared/, and nothing
there imports it. It reads the database tables listed in the plan and writes
only its own mf_* tables.
"""
from __future__ import annotations

RULESET_VERSION = "3"

DIMS: tuple[str, ...] = ("PLACE", "STAND", "DOC", "GAP", "EVID", "ASK", "ALT", "LAW")
GATE_DIMS: tuple[str, ...] = ("GAP", "EVID", "ALT", "LAW")
