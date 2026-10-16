"""Model-free substantive scoring, fully parallel to v3.

Plan: docs/plans/model-free-scoring-plan-parallel.md
Package reference: docs/reference/model-free-scoring-package.md

This package imports nothing from scripts/substance/ or shared/. Its one
outside dependency is the comment-sentences package
(packages/comment-sentences, stored_units), the one method that splits a
comment into sentences. Nothing outside imports this package but
scripts/score_model_compare.py. It reads the tables listed in
docs/model-free-scoring.md and writes only its own mf_* tables.
"""
from __future__ import annotations

RULESET_VERSION = "3"

DIMS: tuple[str, ...] = ("PLACE", "STAND", "DOC", "GAP", "EVID", "ASK", "ALT", "LAW")
GATE_DIMS: tuple[str, ...] = ("GAP", "EVID", "ALT", "LAW")
