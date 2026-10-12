"""Shared bare-word scanning — the one scanner behind the review sheet, the LLM
adjudicator, and the Entities page's task counts.

"Bare words" are the single-word roadless-area names excluded from the deterministic
match vocabulary ("Security", "Dry", "Johnson", "Lake"). This module finds their
boundary-guarded occurrences in comment text as CANDIDATES — nothing here tags
anything or writes to the database.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.entity_tagging.run_pass import _boundary_ok  # noqa: E402


def bare_names(conn, ctx):
    """The excluded single-word area names, with each name's candidate areas
    (forest, state) for prompt context. Returns {name: [(forest, state), ...]}."""
    rows = conn.execute(ctx.render_sql(
        "SELECT name, forest, state FROM {analysis}.roadless_areas"
        " WHERE name NOT LIKE '% %' ORDER BY name, forest")).fetchall()
    out = {}
    for name, forest, state in rows:
        out.setdefault(name, []).append((forest, state))
    return out


# Range names that collide with an area name without any forest sharing the
# prefix — not derivable from the reference tables, so curated here.
CURATED_COLLISIONS = {"Smoky Mountains"}


def collision_names(conn, ctx):
    """Multi-word area names whose deterministic tags are ambiguous: a National
    Forest's name starts with the area's name ("White Mountain" → White Mountain
    National Forest), or the name is a curated range collision. These go through
    the same LLM adjudication lane as the bare single-word names — their tags
    already exist in comment_areas; the verdicts say which refer to the area.
    Returns {name: [(forest, state), ...]} like bare_names."""
    rows = conn.execute(ctx.render_sql(
        "SELECT a.name, a.forest, a.state FROM {analysis}.roadless_areas a"
        " WHERE a.name LIKE '% %'"
        "   AND (EXISTS (SELECT 1 FROM {analysis}.forests f"
        "                WHERE f.name LIKE a.name || '%%')"
        "        OR a.name IN (SELECT value FROM json_each(?)))"
        " ORDER BY a.name, a.forest"), (json.dumps(sorted(CURATED_COLLISIONS)),)).fetchall()
    out = {}
    for name, forest, state in rows:
        out.setdefault(name, []).append((forest, state))
    return out


def build_automaton(names):
    import ahocorasick

    auto = ahocorasick.Automaton()
    for name in names:
        auto.add_word(name.lower(), (len(name), name))
    auto.make_automaton()
    return auto


def iter_bare_hits(conn, ctx, auto):
    """Stream (comment_id, comment_text, name, start, end_inclusive) for every
    boundary-guarded bare-name occurrence, in comment_id order.

    Scans v_truly_unique_comments, NOT v_source_comments: the adjudicator asks a
    paid model whether a word in a given text names an area, and a form letter's
    signers all carry the same text. The view is the corpus's established
    not-a-duplicate set — unique by full text AND by middle content, so a
    template child whose only difference is a name or town at the top is
    excluded — and it is the same population run_pipeline and the embeddings
    stage process.

    Verdicts are carried to the excluded members by their dedup group, so
    nothing loses a tag; what is dropped is paying to ask the same question of
    the same text once per signature.
    """
    with conn.cursor() as cur:
        cur.execute(ctx.render_sql(
            "SELECT comment_id, comment_text FROM {analysis}.v_truly_unique_comments"
            " WHERE comment_text IS NOT NULL ORDER BY comment_id"))
        for comment_id, text in cur:
            lowered = text.lower()
            for end, (plen, name) in auto.iter(lowered):
                start = end - plen + 1
                if _boundary_ok(lowered, start, end):
                    yield comment_id, text, name, start, end
