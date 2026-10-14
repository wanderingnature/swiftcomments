"""Substance scoring — the screen-driven queue and the 8-dimension instrument.

WHO stands for a group is the partition's decision ({analysis}.comment_group,
built by build_comment_groups.py BEFORE this step): one analysis carrier per
group, so a duplicate is never sent twice. WHICH carriers are worth a call is
the mechanical screen's decision ({analysis}.substance_screen, built by
mechanical_screens.py): class A only, unless the operator says otherwise.
WHAT TEXT is sent is the shared-content layer's decision (shared_text.py): the
submitter's own text, with a campaign's shared text scored ONCE on the group's
carrier. See docs/design/rescore-queue-design.md.

The instrument is shared.instrument.SCORING_INSTRUMENT — v3, the reduced-ask
instrument: the model returns five spans, one GAP level and four yes/no answers
and NO scores, and grade.py produces the seven dimensions plus PLACE, DOC,
topics, the flags and T2/T4 from the text itself
(docs/design/reduced-ask-scoring-instrument.md). Its user message is the comment
alone — no preamble, which is the form it was measured in.

--instrument v2 is the earlier one, kept runnable so an old row can be
reproduced: docs/instruments/substantive-scoring-v2.md plus a compact
machine-detected preamble (entities, citation / deficiency / first-person
flags, shared-content cluster size). Nothing downstream reads its rows any
more. LAW is mechanical under both (confirmed citations in the submitter's OWN
text) and never the model's judgment.

Concurrent, incremental (skips what is already scored under this instrument).
Own-score rows upsert into {analysis}.substance_scores; exemplar and delta
results land in {analysis}.substance_score_parts for assemble_scores.py. Run
stats go to substance_artifacts — the DB is the source of truth; no files.

    make score-model                 every class A comment the model has not read
    make score-model LIMIT=200       the first 200 calls of the queue, then exit
    make score-model JSON=dir        also one JSON file per comment (shared/score_json.py),
                               for make compare-scores beside the rules' reading

Ported from rtca: reads and writes data/roadless.sqlite through shared/db.py;
the server and the model from .env (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL,
LLM_PROVIDER; plan 5.2 edit 8); the instrument is read from its quoted block
(edit 13); v3 is the one instrument the repository ships.
"""

import argparse
import json
import sys
import threading
import time
from itertools import zip_longest
from pathlib import Path
from queue import Empty, Queue

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_HERE.parent))   # scripts/substance

from shared import db, score_json
from shared.instrument import SCORING_INSTRUMENT, model_of, same_weights
from shared.project_context import add_project_argument, context_from_args
from shared.llm_client import ChatClient, EndpointNotReady

import grade
import shared_text

DIMS = ["PLACE", "STAND", "DOC", "GAP", "EVID", "ASK", "ALT", "LAW"]

# The rubric object itself is ~250 completion tokens, but a REASONING model
# (qwen3.8-27b, and the cloud endpoint) spends the cap thinking first and the
# answer never leaves the think channel if it runs out — finish_reason=length,
# unparseable, and five identical retries that cannot succeed. 1800 was enough
# for short campaign letters and truncated on the first long own-text comment.

# The instrument's boolean flags (Section B). Requested and persisted in full — every field
# the rubric defines is collected; nothing the model emits is dropped.
FLAGS = ["attachments_referenced", "data_offered", "mischaracterization",
         "off_topic_content", "incorporates_by_reference"]

# Results are written every this many completed calls, and the progress line
# prints on the same interval.
CHECKPOINT_EVERY = 10


def band_for(strength: int) -> str:
    if strength <= 5:
        return "minimal"
    if strength <= 11:
        return "marginal"
    if strength <= 17:
        return "developed"
    return "strong"


def law_sets(ctx, shapes):
    """(own_law_ids, shared_law_ids) — comments with a MECHANICALLY confirmed
    legal-authority citation, SPLIT BY WHOSE TEXT IT IS.

    The entity-tagging pass (full-corpus scan) is the ground truth for LAW:
    validated 2026-09-08, only ~3-22% of LLM LAW scores had any detectable
    citation, so the model's LAW measures register, not law, and is discarded.
    But a bare comment-level set credits the ORGANIZER's citation to every
    signer of a form letter — LAW=2 alone sets the gate. The own/shared split
    puts a campaign's citation on the campaign's exemplar, where it is scored
    once, and leaves the signer with what the signer wrote.
    """
    with db.connect(**ctx.db_config) as conn:
        scopes = shared_text.citation_scopes(conn, ctx.render_sql, shapes)
    return ({c for c, s in scopes.items() if s["own"]},
            {c for c, s in scopes.items() if s["shared"]})


def law_cited_for(kind, own_ids, shared_ids):
    """The LAW set that applies to a queue item: an exemplar item scores the
    campaign's SHARED text, everything else scores the submitter's own."""
    return shared_ids if kind == "exemplar" else own_ids


def item_text(kind, comment_id, shapes):
    """The text a queue item scores: a campaign's SHARED text on an exemplar
    item, the submitter's OWN text everywhere else. One definition, because the
    batch parser has to recover at parse time exactly what was sent."""
    shape = shapes[comment_id]
    return shape.shared_text if kind == "exemplar" else shape.own_text


def grading_tags(ctx):
    """The tag inputs grade.py reads, per comment_id: the confirmed-authority
    matched texts (an EVID span that holds one is legal authority, which earns
    no EVID at any level) and the named entities (an ORG/PERSON/WORK_OF_ART
    inside a span is a named source).

    Loaded once per run from the two tables the entity-tagging pass writes.
    v3 only — under v2 the model scores those dimensions itself.
    """
    auth, ents = {}, {}
    with db.connect(**ctx.db_config) as conn:
        for cid, matched in conn.execute(ctx.render_sql(
                "SELECT comment_id, matched_text FROM {analysis}.comment_authorities")):
            auth.setdefault(cid, []).append(matched)
        for cid, etype, etext in conn.execute(ctx.render_sql(
                "SELECT comment_id, entity_type, entity_text"
                " FROM {analysis}.named_entities")):
            ents.setdefault(cid, []).append((etype, etext))
    return {"authorities": auth, "named_entities": ents}


def apply_v3_grade(obj, comment_id, text, tags, law_cited):
    """v3: the model read, code grades — in place, before finalize_record.

    The model returned five spans, the GAP level and four yes/no answers and no
    scores at all. grade.py turns the span plus its yes/no into each of EVID,
    ASK, ALT and STAND, and reads the text itself for PLACE, DOC, topics, the
    two flags, T2, T4 and M4 (docs/design/reduced-ask-scoring-instrument.md).

    `text` is what the item scored, so every code field is computed over exactly
    the words that were sent. Shared by the synchronous scorer and the batch
    parser, the way finalize_record is, so both transports grade identically.
    """
    graded = grade.grade(obj, text, text, {
        "authorities": tags["authorities"].get(comment_id, []),
        "named_entities": tags["named_entities"].get(comment_id, []),
        "law_cited": comment_id in law_cited,
    })
    obj["scores"] = dict(graded["scores"])
    obj["moves"] = graded["moves"]
    obj["targets"] = graded["targets"]
    obj["topics"] = graded["topics"]
    obj["originality"] = graded["originality"]
    obj["language"] = graded["language"]
    obj["flags"] = {
        "attachments_referenced": graded["attachments_referenced"],
        "incorporates_by_reference": graded["incorporates_by_reference"],
    }
    # Which rule produced each level, and what it matched. substance_scores has
    # no column for it; the parts table stores the whole record as jsonb, so an
    # exemplar or delta row keeps its trace.
    obj["rules"] = graded["rules"]
    return obj


def finalize_record(obj, comment_id, was_floored, law_cited=None):
    """Apply the MECHANICAL rubric derivations to a raw model object, in place.

    Gate and strength come from the eight dimension scores, not the model's own
    arithmetic (kept as *_reported to measure drift). Shared by the synchronous scorer
    and the batch parser so both produce byte-identical records for the same model output.

    `law_cited` (set of comment_ids, from law_sets via law_cited_for): when given, LAW is
    MECHANICAL — 2 if the entity-tagging pass confirmed a legal-authority citation,
    else 0. The model's LAW value is discarded (level 3, statute-to-gap linkage,
    is a separate judgment restricted to confirmed citers; not scored here).
    """
    obj["comment_id"] = comment_id
    obj["was_floored"] = was_floored
    # The rubric defines every dimension as 0-3 and the DB enforces it (substance_scores
    # CHECK (<dim> BETWEEN 0 AND 3)). LM Studio's structured-output grammar pins the integer
    # TYPE but not the numeric bound, so the local model occasionally returns e.g. ALT=4 -
    # which the DB rejects, aborting the whole batch upsert and the Score step. Clamp to the
    # instrument's range here, the one derivation point both the sync scorer and the cloud
    # batch parser share, so a single out-of-range score can't take down the run.
    s = {d: min(3, max(0, int(obj.get("scores", {}).get(d, 0) or 0))) for d in DIMS}
    if law_cited is not None:
        s["LAW"] = 2 if comment_id in law_cited else 0
    obj["scores"] = s  # persist the clamped values: write_score_outputs reads obj["scores"]
    strength = sum(s.values())
    gate_dims = [d for d in ("GAP", "EVID", "ALT", "LAW") if s[d] >= 2]
    obj["strength_reported"] = obj.get("strength")
    obj["gate_reported"] = obj.get("gate")
    obj["strength"] = strength
    obj["strength_check"] = strength
    obj["gate"] = len(gate_dims) > 0
    obj["gate_basis"] = gate_dims
    obj["band"] = band_for(strength)
    return obj


def json_record(obj, model):
    """A finalized direct record in the shape shared with the rules' reading
    (shared/score_json.py): the eight levels, strength, gate and its basis,
    band, no A level (make rate gives it), and as evidence the model's five
    spans with the yes/no answer and the rule that graded each, and the
    rationale."""
    spans = obj.get("evidence") or {}
    rules = obj.get("rules") or []          # grade.py's list of {rule, match}
    answers = {"EVID": obj.get("evid_applied"), "ASK": obj.get("ask_names_action_and_subject"),
               "ALT": obj.get("alt_distinct"), "STAND": obj.get("stand_this_place"),
               "GAP": obj.get("gap")}
    evidence = [{"dimension": d, "span": spans.get(d), "answer": answers.get(d),
                 "level": obj["scores"].get(d),
                 "rules": [r for r in rules if str(r.get("rule", "")).startswith(d + ".")]}
                for d in ("GAP", "EVID", "ASK", "ALT", "STAND")]
    evidence.append({"dimension": "rationale", "span": obj.get("rationale")})
    return {
        "comment_id": obj["comment_id"], "scorer": "model", "instrument": obj["instrument_version"],
        "model": model, "levels": {d: int(obj["scores"][d]) for d in DIMS},
        "strength": int(obj["strength"]), "gate": bool(obj["gate"]),
        "gate_basis": list(obj.get("gate_basis", [])), "band": obj["band"], "a_level": None,
        "evidence": evidence,
    }


def next_steps(*steps):
    """The house rule: a step in a chain ends by printing the command that
    follows it, in full and copy-pasteable, with the reason it is next.

    Nothing here is abbreviated and nothing above it is truncated — a run's
    output is the whole record of what happened plus what to run now.
    """
    print()
    for i, (cmd, why) in enumerate(steps):
        print(f"{'NEXT:' if i == 0 else 'THEN:'} {cmd}")
        print(f"      {why}")


def dry_run_report(requests, instrument, system_prompt, destination,
                   next_command, extra=()):
    """What a run WOULD do, printed, with nothing called and nothing written.

    A corpus run under a new instrument is the whole class-A queue at once, on
    paid hardware. This is the look before that. Called after the queue is
    built, so every number is the real queue's, not an estimate.

    The id list comes FIRST and the summary LAST: the list is as long as the
    queue, so a summary printed above it scrolls off the screen and the one
    thing wanted — how many — is the thing that gets lost.
    """
    by_kind = {}
    for r in requests:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    chars = [len(r["user"]) for r in requests]
    print(f"\n=== DRY RUN — no calls made, nothing written ===")
    print(f"the {len(requests)} request id(s), in send order:")
    for r in requests:
        print(f"  {r['request_id']}")
    print("\n=== DRY RUN SUMMARY ===")
    print(f"instrument   {instrument}  ({INSTRUMENTS[instrument]},"
          f" {len(system_prompt):,} chars of system prompt)")
    print(f"queue        {len(requests)} call(s) over"
          f" {len({r['comment_id'] for r in requests})} comment(s)")
    for kind in sorted(by_kind):
        print(f"  {kind:9} {by_kind[kind]}")
    if chars:
        print(f"user message {min(chars):,} min / {sum(chars)//len(chars):,} avg /"
              f" {max(chars):,} max chars")
    print(f"would write  {destination}")
    for line in extra:
        print(line)
    next_steps((next_command, "the same run without --dry-run. Every number above"
                              " is this queue's, not an estimate."))


def user_message(cid, preamble, text):
    """The per-comment user message — identical for the sync scorer and the batch
    generator, so both send the same prompt and get comparable scores.

    An empty preamble sends the comment alone, which is v3's form: the machine
    pre-annotation is a v2 hint, it appears nowhere in the v3 instrument, and
    the 100-comment repeatability runs were made without it.
    """
    head = f"{preamble}\n" if preamble else ""
    return f"{head}COMMENT (comment_id={cid}):\n---\n{text}\n---"


_SCORE_UPSERT = (
    "INSERT INTO {analysis}.substance_scores (comment_id, was_floored, gate, strength, "
    "strength_check, strength_reported, gate_reported, band, place, stand, doc, gap, evid, "
    "ask, alt, law, gate_basis, moves, targets, topics, originality, harm_stated, "
    "issue_count, language, attachments_referenced, data_offered, mischaracterization, "
    "off_topic_content, incorporates_by_reference, scored_by, model, tokens_in, "
    "tokens_out, ms, rationale, scored_via, exemplar_id, instrument_version) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
    "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
    "?, ?, ?) "
    "ON CONFLICT (comment_id) DO UPDATE SET was_floored=EXCLUDED.was_floored, "
    "gate=EXCLUDED.gate, strength=EXCLUDED.strength, strength_check=EXCLUDED.strength_check, "
    "strength_reported=EXCLUDED.strength_reported, gate_reported=EXCLUDED.gate_reported, "
    "band=EXCLUDED.band, place=EXCLUDED.place, stand=EXCLUDED.stand, doc=EXCLUDED.doc, "
    "gap=EXCLUDED.gap, evid=EXCLUDED.evid, ask=EXCLUDED.ask, alt=EXCLUDED.alt, "
    "law=EXCLUDED.law, gate_basis=EXCLUDED.gate_basis, moves=EXCLUDED.moves, "
    "targets=EXCLUDED.targets, topics=EXCLUDED.topics, "
    "originality=EXCLUDED.originality, harm_stated=EXCLUDED.harm_stated, "
    "issue_count=EXCLUDED.issue_count, language=EXCLUDED.language, "
    "attachments_referenced=EXCLUDED.attachments_referenced, "
    "data_offered=EXCLUDED.data_offered, mischaracterization=EXCLUDED.mischaracterization, "
    "off_topic_content=EXCLUDED.off_topic_content, "
    "incorporates_by_reference=EXCLUDED.incorporates_by_reference, "
    "scored_by=EXCLUDED.scored_by, "
    "model=EXCLUDED.model, tokens_in=EXCLUDED.tokens_in, tokens_out=EXCLUDED.tokens_out, "
    "ms=EXCLUDED.ms, rationale=EXCLUDED.rationale, "
    "scored_via=EXCLUDED.scored_via, exemplar_id=EXCLUDED.exemplar_id, "
    "instrument_version=EXCLUDED.instrument_version, scored_at=CURRENT_TIMESTAMP")

_PART_UPSERT = (
    "INSERT INTO {analysis}.substance_score_parts (comment_id, part, place, stand, doc, "
    "gap, evid, ask, alt, law, strength, gate, band, model, instrument_version, "
    "rationale, record) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
    "?, ?, ?) ON CONFLICT (comment_id, part) DO UPDATE SET "
    "place=EXCLUDED.place, stand=EXCLUDED.stand, doc=EXCLUDED.doc, gap=EXCLUDED.gap, "
    "evid=EXCLUDED.evid, ask=EXCLUDED.ask, alt=EXCLUDED.alt, law=EXCLUDED.law, "
    "strength=EXCLUDED.strength, gate=EXCLUDED.gate, band=EXCLUDED.band, "
    "model=EXCLUDED.model, instrument_version=EXCLUDED.instrument_version, "
    "rationale=EXCLUDED.rationale, record=EXCLUDED.record, scored_at=CURRENT_TIMESTAMP")


def write_score_parts(ctx, records, model=None):
    """Persist raw exemplar/delta results into {analysis}.substance_score_parts.

    A member's stored score is the field-wise max of its exemplar and its own
    delta (assemble_scores.py), which is a DERIVED row — the parts table keeps
    what each call actually returned, so assembly can be re-run and no
    captured model output is ever overwritten by it.
    """
    rows = []
    for r in records:
        s = r.get("scores", {})
        rows.append((
            r["comment_id"], r["scored_via"], *[s.get(d) for d in DIMS],
            r.get("strength"), r.get("gate"), r.get("band"),
            r.get("model") or model, r["instrument_version"],
            (r.get("rationale", "") or "").replace("\n", " "), json.dumps(r)))
    with db.connect(**ctx.db_config) as conn:
        with conn.cursor() as cur:
            cur.executemany(ctx.render_sql(_PART_UPSERT), rows)
        conn.commit()


def write_results(ctx, records, model=None):
    """Route finalized records by provenance: 'direct' rows are the comment's
    own score and go straight to substance_scores; 'exemplar' and 'delta' are
    PARTS that assemble_scores.py combines into member rows."""
    direct = [r for r in records if r.get("scored_via") == "direct"]
    parts = [r for r in records if r.get("scored_via") in ("exemplar", "delta")]
    if direct:
        write_score_outputs(ctx, direct, model=model)
    if parts:
        write_score_parts(ctx, parts, model=model)
    return len(direct), len(parts)


def write_score_outputs(ctx, records, model=None, table="substance_scores"):
    """Upsert scored records into {analysis}.substance_scores — the source of truth. The eight
    dimensions become their own 0-3 columns. Shared by the synchronous scorer and the batch
    parser so both persist identically. Idempotent per comment_id (incremental checkpoints just
    re-upsert the growing set). `table` is substance_scores_merged for a --merged run, which
    has the same columns."""
    rows = []
    for r in records:
        s = r.get("scores", {})
        f = r.get("flags") or {}
        rows.append((
            r["comment_id"], r["was_floored"], r.get("gate"), r.get("strength"),
            r["strength_check"], r.get("strength_reported"), r.get("gate_reported"),
            r.get("band"), *[s.get(d) for d in DIMS],
            json.dumps(r.get("gate_basis", [])), json.dumps(r.get("moves", [])),
            json.dumps(r.get("targets", [])), json.dumps(r.get("topics", [])),
            r.get("originality"), r.get("harm_stated"), r.get("issue_count"),
            r.get("language"), *[f.get(k) for k in FLAGS],
            r.get("scored_by"), r.get("model") or model,
            r.get("tokens_in"), r.get("tokens_out"), r.get("ms"),
            (r.get("rationale", "") or "").replace("\n", " "),
            r.get("scored_via", "direct"), r.get("exemplar_id"),
            r.get("instrument_version", "v1")))
    with db.connect(**ctx.db_config) as conn:
        with conn.cursor() as cur:
            cur.executemany(ctx.render_sql(
                _SCORE_UPSERT.replace("{analysis}.substance_scores ", f"{{analysis}}.{table} ")),
                rows)
        conn.commit()


# A queue item's kind decides what text is sent and how the result is stored.
# 'direct' rows are the comment's own score; 'exemplar' scores a campaign's
# shared text once for its whole cluster; 'delta' scores a member's own
# contribution, to be max'd with its exemplar in assemble_scores.py.
_SCORED_VIA = {"unique": "direct", "exemplar": "exemplar", "delta": "delta"}
_KIND_ORDER = {"exemplar": 0, "delta": 1, "unique": 2}


def already_called(direct_rows, part_rows, model):
    """The request ids a run under `model` can skip: direct rows and parts
    stored under the instrument by the same weights (shared.instrument
    .same_weights). `direct_rows` is (comment_id, model) over substance_scores
    rows with scored_via = 'direct'; `part_rows` is (comment_id, part, model)
    over substance_score_parts.

    Only a 'direct' row answers a unique item. An 'exemplar' or 'delta' row in
    substance_scores is written by assemble_scores from the parts, with no
    call and no model; counting it as done skipped the own call of a comment
    that had left its family (4 comments, 2026-09-20). A row under another
    model is not this run's score: 508 delta parts from the 9B were kept in a
    27B corpus the same day.
    """
    done = {f"{c}#direct" for c, m in direct_rows if same_weights(m, model)}
    done |= {f"{c}#{p}" for c, p, m in part_rows if same_weights(m, model)}
    return done


def build_scoring_requests(ctx, *, model, classes=("A",), limit=None, rescore=False,
                           instrument=SCORING_INSTRUMENT, sliced=False):
    """The screen-driven scoring queue — what is worth paying an LLM for.

    The partition ({analysis}.comment_group) decides WHO stands for a group:
    its analysis carrier, one per group, fixed before this step. The
    mechanical screen ({analysis}.substance_screen) decides WHICH carriers are
    worth a call. The shared-content layer (shared_text) decides WHAT TEXT is
    sent. Three kinds, per docs/design/rescore-queue-design.md:

      unique    a carrier outside every family, in `classes` -> its own text
      exemplar  the carrier of a group with a family_id, always -> the family's shared text
      delta     a family member in `classes` with own text   -> its own text only

    Every other member of a family or campaign group INHERITS the carrier's
    score without a call (assemble_scores.py). A member of an exact or
    middle group is the same text as its carrier and is resolved through the
    group, never sent; when that class is a family by itself, its carrier's
    item is an exemplar, not a unique. The model never sees boilerplate
    except on the exemplar item, so it is never asked to guess what is
    templated — the mechanical layers already know.

    Returns (requests, shapes). Each request carries request_id (the batch
    custom_id: "<comment_id>#<kind>", so an exemplar comment can also carry
    its own delta item), comment_id, kind, exemplar_id, system, user.
    Shared by the synchronous scorer and the batch generator, so local and
    cloud-batch stay one pipeline with two transports.
    """
    print("make score-model: reading the floor's survivors, the screen, the floor flags, the"
          " named entities, the partition and the shared text; then the queue of calls"
          " for class(es) " + "/".join(classes) + " not yet read under"
          f" {instrument} by {model_of(model)}", flush=True)
    with db.connect(**ctx.db_config) as conn:
        rows = shared_text.load_corpus(conn, ctx.render_sql)
        if not rows:
            raise SystemExit("No floor-filter survivors — run the floor filter first.")
        screen = dict(conn.execute(ctx.render_sql(
            "SELECT comment_id, screen_class FROM {analysis}.substance_screen")))
        flags_by_id = {r[0]: {"has_citation": r[1], "has_deficiency": r[2],
                              "has_firstperson": r[3]}
                       for r in conn.execute(ctx.render_sql(
                           "SELECT comment_id, has_citation, has_deficiency,"
                           " has_firstperson FROM {analysis}.substance_floor"))}
        ents_by_id = {}
        for cid, etype, etext in conn.execute(ctx.render_sql(
                "SELECT comment_id, entity_type, entity_text"
                " FROM {analysis}.named_entities")):
            ents_by_id.setdefault(cid, []).append((etype, etext))
        done = set()
        if not rescore:
            # Only a 'direct' row is a call this run made for the comment's
            # own text; inherited, exemplar and delta rows in substance_scores
            # are assembled from the parts without a call, and one exemplar
            # can inherit to thousands. And only a row from the same weights
            # is this run's score (already_called).
            done = already_called(
                [tuple(r) for r in conn.execute(ctx.render_sql(
                    "SELECT comment_id, model FROM {analysis}.substance_scores"
                    " WHERE instrument_version = ?"
                    " AND scored_via = 'direct'"), (instrument,))],
                [tuple(r) for r in conn.execute(ctx.render_sql(
                    "SELECT comment_id, part, model"
                    " FROM {analysis}.substance_score_parts"
                    " WHERE instrument_version = ?"), (instrument,))],
                model)

    missing = [cid for cid, _t in rows if cid not in screen]
    if missing:
        raise SystemExit(
            f"{len(missing)} survivors have no screen class — run"
            " scripts/substance/mechanical_screens.py --write first."
            " The screen decides what gets scored; it cannot be skipped.")

    # WHO is a group is the partition's decision, made before this step. This
    # used to re-derive groups from shared_text.clusters here, which is what
    # left the scorer and the partition naming different representatives and
    # sending comments the partition never named (ISSUE-8,
    # docs/design/pipeline-issues.md). WHAT TEXT is the stored family
    # attribution, written by the same build.
    with db.connect(**ctx.db_config) as conn:
        shapes = shared_text.load_shapes(conn, ctx.render_sql)
        groups = {gid: (kind, carrier, size, family_id)
                  for gid, kind, carrier, size, family_id in conn.execute(ctx.render_sql(
                      "SELECT group_id, group_kind, analysis_comment_id, size, family_id"
                      " FROM {analysis}.comment_group"))}
        members, has_own_text, group_of = {}, {}, {}
        for cid, gid, own in conn.execute(ctx.render_sql(
                "SELECT comment_id, group_id, has_own_text"
                " FROM {analysis}.comment_group_member")):
            members.setdefault(gid, []).append(cid)
            has_own_text[cid] = own
            group_of[cid] = gid
    if not groups:
        raise SystemExit(
            "comment_group is empty — run"
            " scripts/substance/build_comment_groups.py --rebuild --write first."
            " The partition decides who is scored; it precedes this step.")
    ungrouped = [cid for cid, _t in rows if cid not in group_of]
    if ungrouped:
        raise SystemExit(
            f"{len(ungrouped)} survivor(s) are in no group — rebuild the"
            " partition (build_comment_groups.py --write) before scoring."
            " All of them:\n  " + "\n  ".join(ungrouped))

    items = []
    for gid, (kind, carrier, size, family_id) in groups.items():
        if carrier is None or carrier not in shapes:
            continue                        # no member survived the floor
        if family_id is not None:
            # A group in a family — kind family or campaign, or an exact or
            # middle class that is a family by itself — scores the family's
            # shared text once, on the carrier, queued regardless of the
            # carrier's own class: the item scores the FAMILY's text, and the
            # class was computed on own text.
            items.append(("exemplar", carrier, carrier,
                          item_text("exemplar", carrier, shapes), size))
            for cid in members[gid]:
                if (cid in shapes and has_own_text[cid]
                        and screen[cid] in classes):
                    items.append(("delta", cid, carrier,
                                  item_text("delta", cid, shapes), size))
        elif screen[carrier] in classes:
            items.append(("unique", carrier, None,
                          item_text("unique", carrier, shapes), 1))

    system_prompt = load_system_prompt(instrument, sliced=sliced)
    items.sort(key=lambda it: (_KIND_ORDER[it[0]], it[1]))
    # Round-robin the kinds. Sorted by kind, a --limit pilot samples ONLY the
    # first kind (a 20-item pilot returned 20 exemplars and nothing else),
    # which tells you nothing about the other three.
    buckets = {}
    for it in items:
        buckets.setdefault(it[0], []).append(it)
    items = []
    for row in zip_longest(*(buckets[k] for k in sorted(buckets, key=lambda k: _KIND_ORDER[k]))):
        items.extend(it for it in row if it is not None)
    requests = []
    for kind, cid, exemplar_id, text, group_size in items:
        rid = f"{cid}#{_SCORED_VIA[kind]}"
        if rid in done or not text.strip():
            continue
        preamble = "" if instrument == "v3" else build_preamble(
            cid, ents_by_id.get(cid, []), flags_by_id[cid], group_size)
        requests.append({"request_id": rid, "comment_id": cid, "kind": kind,
                         "scored_via": _SCORED_VIA[kind],
                         "exemplar_id": exemplar_id,
                         "instrument_version": instrument,
                         "system": system_prompt,
                         "user": user_message(cid, preamble, text),
                         # the words this item scores: grade.py reads them for
                         # PLACE, DOC, topics, the flags and T2 under v3.
                         "text": text,
                         "floored": False})
        if limit and len(requests) >= limit:
            break
    counts = {}
    for r in requests:
        counts[r["kind"]] = counts.get(r["kind"], 0) + 1
    print(f"queue: {len(requests)} call(s) for class(es) {'/'.join(classes)}"
          f" — " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
          + (f"; {len(done)} already scored under {instrument} by {model_of(model)}"
             if done else "")
          + (f"; --limit {limit}: the first {limit} of the queue" if limit else "")
          + "; writes substance_scores (direct) and substance_score_parts (exemplar, delta)",
          flush=True)
    return requests, shapes

def build_merged_requests(ctx, *, model, limit=None, rescore=False,
                          instrument=SCORING_INSTRUMENT, comment_ids=None):
    """The --merged queue: every comment in {analysis}.v_merged_comments, scored on its
    merged text — its own text followed by its attachments' text — once, as itself.

    A trial beside the corpus, not part of it (docs/plans/attachment-text-merge.md): no
    screen, group or carrier decides anything here, and the rows go to
    {analysis}.substance_scores_merged, never substance_scores. Incremental the same way
    as the main queue: a comment already scored there under this instrument by the same
    weights is skipped. v3 only — the v2 preamble is built from the comment's own floor
    flags, which say nothing about its attachments. `comment_ids` scores only those; an id
    with no merged row is an error, not a silent skip.
    """
    if instrument != "v3":
        raise SystemExit("--merged scores under v3 only: the v2 preamble describes the"
                         " comment's own text, not its attachments.")
    with db.connect(**ctx.db_config) as conn:
        rows = [tuple(r) for r in conn.execute(ctx.render_sql(
            "SELECT comment_id, merged_text FROM {analysis}.v_merged_comments"
            " ORDER BY comment_id"))]
        done = set() if rescore else already_called([tuple(r) for r in conn.execute(ctx.render_sql(
            "SELECT comment_id, model FROM {analysis}.substance_scores_merged"
            " WHERE instrument_version = ?"), (instrument,))], [], model)
    if not rows:
        raise SystemExit("v_merged_comments is empty — run scripts/attachment_text.py"
                         " --write first.")
    if comment_ids:
        missing = sorted(set(comment_ids) - {cid for cid, _t in rows})
        if missing:
            raise SystemExit("no merged row (no attachment with text) for: "
                             + ", ".join(missing))
        rows = [(cid, t) for cid, t in rows if cid in set(comment_ids)]
    system_prompt = load_system_prompt(instrument)
    requests = []
    for cid, text in rows:
        if f"{cid}#direct" in done:
            continue
        requests.append({"request_id": f"{cid}#direct", "comment_id": cid, "kind": "unique",
                         "scored_via": "direct", "exemplar_id": None,
                         "instrument_version": instrument, "system": system_prompt,
                         "user": user_message(cid, "", text), "text": text,
                         "floored": False})
        if limit and len(requests) >= limit:
            break
    print(f"merged queue: {len(requests)} call(s) of {len(rows)} merged comment(s)"
          + (f"; {len(done)} already scored under {instrument} by {model_of(model)}"
             if done else ""), flush=True)
    return requests


def merged_tags(ctx, texts):
    """grade.py's tag inputs and the LAW set, computed over the MERGED text.

    The stored tags (comment_authorities, named_entities) were found in the comment's
    own text only; an attachment's citations and sources are in none of them. So the
    same detectors run here, in memory, over what is scored: the entity-tagging strict
    pass's legal-authority vocabulary and citation detectors
    (scripts/entity_tagging/run_pass.py) and the linguistic pass's spaCy model
    (en_core_web_md, entities lowercased as extract_linguistic_patterns.py stores them).
    All of a merged text is the commenter's submission, so any confirmed authority puts
    the comment in the LAW set. Nothing is written.
    """
    import spacy
    from scripts.entity_tagging.run_pass import (StrictMatcher, _Rendering,
                                                 build_vocabulary, run_detectors)
    with db.connect(**ctx.db_config) as conn:
        with conn.cursor() as cur:
            built = build_vocabulary(_Rendering(cur, ctx))
    matcher = StrictMatcher({"authorities": built["vocab"]["authorities"]})
    nlp = spacy.load("en_core_web_md", disable=["textcat"])
    auth, ents, law = {}, {}, set()
    for cid, text in texts.items():
        found = matcher.find(text).get("authorities", [])
        detected = run_detectors(text, [(s, e) for _v, _m, s, e in found],
                                 built["doi_to_key"])[0]
        auth[cid] = [m for _v, m, _s, _e in found] + [m for _v, m in detected]
        if auth[cid]:
            law.add(cid)
        nlp.max_length = max(nlp.max_length, len(text) + 1)
        ents[cid] = [(e.label_, e.text.strip().lower()) for e in nlp(text).ents]
    return {"authorities": auth, "named_entities": ents}, law


# The output schema lives beside the instrument (docs/instruments/
# substantive-scoring-v3.schema.json) and is edited with it. v3 asks the model
# for nine fields carrying thirteen values — five spans, the GAP level, four
# yes/no answers, moves and targets, and the rationale — and grade.py turns
# them into the seven dimension scores. The v1 and v2 instruments and the v2
# schema are rtca's history and are not in this repository: v3 is the one
# instrument here, and a row of another version is not expected in the file.
SCHEMAS = {
    "v3": json.loads((_REPO_ROOT / "docs" / "instruments"
                      / "substantive-scoring-v3.schema.json").read_text(encoding="utf-8")),
}


INSTRUMENTS = {"v3": "substantive-scoring-v3.md"}

# The prompt is the quoted block under this heading of the instrument file,
# up to SECTION D (plan 5.2 edit 13); the label above the heading and the
# deployment notes below the line are for the person running it.
_PROMPT_HEADING = "\n# System prompt\n"


def load_system_prompt(version: str = SCORING_INSTRUMENT, sliced: bool = False) -> str:
    """The instrument as the system prompt — everything before SECTION D
    (the deployment notes).

    v2 is the default: LAW and originality are mechanical downstream and the
    instrument tells the model to stop scoring them, the Generalities
    prohibition kills propositions true of any proposal, and its few-shots
    include the negative calibration ("the eloquent generality") whose
    absence let policy opinions gate in as substantive.

    `sliced` is the v1-only condensed prompt: a LOCAL-latency hack (15s vs
    75s/call on the 7B box) that drops the few-shot examples. It has no place
    in a paid run — billing is GPU-MINUTES, so prefill on a shared system
    prompt is nearly free.
    """
    if version not in INSTRUMENTS:
        raise SystemExit(f"unknown instrument {version!r} — one of {sorted(INSTRUMENTS)}")
    text = (_REPO_ROOT / "docs" / "instruments"
            / INSTRUMENTS[version]).read_text(encoding="utf-8")
    if not sliced:
        start = text.find(_PROMPT_HEADING)
        if start == -1:
            raise SystemExit(f"{INSTRUMENTS[version]} has no '# System prompt' heading:"
                             " the prompt is the quoted block under it (docs/prompts.md)")
        start += len(_PROMPT_HEADING)
        cut = text.find("# SECTION D", start)
        block = text[start:cut] if cut != -1 else text[start:]
        return unquote(block)
    if version != "v1":
        raise SystemExit("--sliced-prompt exists only for the v1 instrument;"
                         " v2 is deployed whole (see its deployment notes).")
    start = text.find("## The eight dimensions")
    end = text.find("## Prohibited scoring influences")
    core = text[start:end].strip() if start != -1 and end != -1 else text
    # The classification-field vocabularies (M1-M5, T1-T4, topic codes, originality,
    # harm_stated, the boolean flags) live in "## Classification fields", past the `core`
    # slice — without them the model can't emit the codes and those fields come back empty.
    # Graft the WHOLE section (up to "## Rationale"): every Section-B field is requested
    # and persisted; nothing the instrument defines is dropped.
    fstart = text.find("## Classification fields")
    fend = text.find("## Rationale")
    fields = text[fstart:fend].strip() if fstart != -1 and fend != -1 else ""
    return (
        "You are a classification instrument for public comments on federal agency actions. "
        "You measure how much analytical work a comment does that an agency must address — not "
        "whether it is persuasive, well-written, or correct. Do not let length, register, "
        "fluency, credentials-without-application, emotional intensity, or the commenter's "
        "stance influence any score. Score only what is explicitly present.\n\n"
        + core + "\n\n" + fields +
        "\n\nReturn ONLY the JSON object required by the schema: gate, strength (= sum of the "
        "eight scores), band, scores{...}, gate_basis (dims at/above 2 among GAP/EVID/ALT/LAW), "
        "topics, moves, targets, originality, harm_stated, issue_count (number of distinct "
        "issues the comment raises), language (ISO 639-1 code of the comment's language), "
        "flags{attachments_referenced, data_offered, mischaracterization, off_topic_content, "
        "incorporates_by_reference}, and a 1-2 sentence rationale naming the deciding anchors."
    )


def unquote(block: str) -> str:
    """The prompt text of a Markdown quoted block: one '> ' (or a bare '>') off
    every line. A line without the quote mark is a line the page would render
    outside the prompt, so it is refused rather than sent."""
    lines = block.strip("\n").split("\n")
    out = []
    for line in lines:
        if line.startswith("> "):
            out.append(line[2:])
        elif line.startswith(">"):
            out.append(line[1:])
        elif line == "":
            out.append(line)
        else:
            raise SystemExit(f"the instrument's prompt block has an unquoted line: {line[:80]!r}")
    return "\n".join(out).strip()


def build_preamble(comment_id, ents, flags, group_size) -> str:
    """`group_size` is the SHARED-CONTENT cluster size (shared_text), not
    comment_dedup.duplicate_group_size — the exact-hash count reports 1 for a
    signer of a 10,000-member campaign, because one added sentence changes
    the hash."""
    by_type = {}
    for t, txt in ents:
        by_type.setdefault(t, [])
        if txt not in by_type[t] and len(by_type[t]) < 6:
            by_type[t].append(txt)
    ent_str = "; ".join(f"{t}: {', '.join(v)}" for t, v in by_type.items()) or "none detected"
    return (
        "Machine pre-annotation (hints from lexical analysis — still read the full text; "
        "do not treat absence as proof):\n"
        f"- Named entities -> {ent_str}\n"
        f"- Citation/legal reference present: {'yes' if flags['has_citation'] else 'no'}\n"
        f"- Deficiency language present: {'yes' if flags['has_deficiency'] else 'no'}\n"
        f"- First-person observation present: {'yes' if flags['has_firstperson'] else 'no'}\n"
        f"- This comment shares its text with {group_size} comment(s) in the"
        f" corpus (shared-content cluster size)\n"
    )


def main():
    parser = argparse.ArgumentParser(description="Score floor-filter survivors (the model of .env).")
    add_project_argument(parser)
    # The model and the server are the reader's, from .env (plan 5.2 edit 8):
    # LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, LLM_PROVIDER. Every row is stamped
    # with LLM_MODEL, the queue counts only that model's rows as done, and the
    # assembler reads only its parts. What carries comparability is
    # instrument_version: a v3 score is comparable to a v3 score.
    parser.add_argument("--classes", default="A",
                        help="screen classes to score, comma-separated."
                             " Class A is the planned run; B1/B2 are the"
                             " operator's decision, never a default"
                             " (docs/design/rescore-queue-design.md).")
    parser.add_argument("--limit", type=int, default=None,
                        help="cap the queue (pilots); default is the whole"
                             " queue for the requested classes")
    parser.add_argument("--instrument", default=SCORING_INSTRUMENT,
                        choices=sorted(INSTRUMENTS),
                        help=f"scoring instrument (default {SCORING_INSTRUMENT},"
                             " the version the analysis reads)")
    parser.add_argument("--concurrency", type=int, default=8,
                        help="the most calls in flight; the client starts at one and climbs")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--json", metavar="DIR",
                        help="also write one JSON file per scored comment under DIR, in the"
                             " shape of shared/score_json.py (make compare-scores)")
    # The FULL instrument is the default. The sliced prompt was a LOCAL-latency
    # hack (15s vs 75s/call on the 7B box) that leaked into cloud runs, where
    # billing is GPU-MINUTES — prefill on a shared system prompt is nearly
    # free — and the sliced-out few-shots were exactly the negative
    # calibration ("statement of position only" scoring all zeros) whose
    # absence let policy opinions gate in as substantive.
    parser.add_argument("--sliced-prompt", dest="sliced",
                        action="store_true",
                        help="v1 only: drop the few-shot examples"
                             " (local-latency hack; degrades calibration)")
    parser.add_argument("--dry-run", action="store_true",
                        help="build the queue, print what would be sent, and"
                             " stop. No model call, no row written.")
    parser.add_argument("--merged", action="store_true",
                        help="score the comments of v_merged_comments on their own text"
                             " plus their attachments' text, into substance_scores_merged —"
                             " a trial beside the corpus; substance_scores is not touched"
                             " (docs/plans/attachment-text-merge.md).")
    parser.add_argument("--comment-id", action="append", dest="comment_ids", metavar="ID",
                        help="with --merged: score only this comment (repeatable)")
    parser.add_argument("--rescore", action="store_true",
                        help="re-score every queue item; default is INCREMENTAL — skip what is "
                             "already scored under this instrument, so a re-run picks up just "
                             "the newly collected comments.")
    args = parser.parse_args()
    if args.comment_ids and not args.merged:
        raise SystemExit("--comment-id selects from the --merged queue only.")
    ctx = context_from_args(args)

    # The server and the model of .env; at most --concurrency calls in flight,
    # from one, climbing (shared/llm_client.py).
    client = ChatClient(timeout=args.timeout, max_in_flight=args.concurrency)
    args.model = client.model
    json_dir = Path(args.json) if args.json else None

    classes = tuple(c.strip() for c in args.classes.split(",") if c.strip())
    shapes = None
    if args.merged:
        requests = build_merged_requests(ctx, model=args.model, limit=args.limit,
                                         rescore=args.rescore, instrument=args.instrument,
                                         comment_ids=args.comment_ids)
    else:
        requests, shapes = build_scoring_requests(
            ctx, model=args.model, classes=classes, limit=args.limit,
            rescore=args.rescore, instrument=args.instrument, sliced=args.sliced)
    table = "substance_scores_merged" if args.merged else "substance_scores"
    if not requests:
        print("Nothing new to score — every queue item is already scored under "
              f"instrument {args.instrument} by {model_of(args.model)} (use --rescore to"
              " redo). Tables left unchanged.",
              flush=True)
        return
    system_prompt = requests[0]["system"]  # identical for every request
    if json_dir is not None:
        print(f"one JSON file per scored comment under {json_dir}", flush=True)
    if args.dry_run:
        dry_run_report(
            requests, args.instrument, system_prompt,
            f"{ctx.analysis_schema}.{table}"
            + ("" if args.merged else " + substance_score_parts"),
            "make score-model" + (" --merged" if args.merged else "")
            + (f" LIMIT={args.limit}" if args.limit else ""))
        print(f"would call   {client.model} at {client.base_url}")
        return
    print(f"scoring {len(requests)} call(s) — rows keyed {model_of(args.model)},"
          f" calls via {client.model} at {client.base_url}; a checkpoint every"
          f" {CHECKPOINT_EVERY} calls", flush=True)

    queue = Queue()
    for r in requests:
        queue.put(r)
    total = queue.qsize()

    # SQLite has one writer: the checkpoints from the workers go one at a time.
    write_lock = threading.Lock()

    def write_outputs(snapshot):
        # Route by provenance: own-score rows to substance_scores, exemplar/delta
        # results to substance_score_parts. Both upsert, so incremental runs and
        # checkpoints just re-write the growing set.
        # Stamped with the model, never the endpoint the call went to.
        with write_lock:
            if args.merged:
                write_score_outputs(ctx, snapshot, model=model_of(args.model), table=table)
            else:
                write_results(ctx, snapshot, model=model_of(args.model))

    results, errors = [], []
    lock = threading.Lock()
    done = [0]

    schema = SCHEMAS[args.instrument]
    if args.merged:
        tags, merged_law = merged_tags(ctx, {r["comment_id"]: r["text"] for r in requests})
        own_law = shared_law = merged_law
    else:
        own_law, shared_law = law_sets(ctx, shapes)
        tags = grading_tags(ctx) if args.instrument == "v3" else None

    def score_job(req):
        _t0 = time.perf_counter()
        obj, usage = client.complete(system=system_prompt, user=req["user"],
                                     schema=schema, with_usage=True)
        obj["scored_by"] = client.base_url
        # Token + latency accounting for cost/throughput estimation (per comment).
        obj["tokens_in"] = usage.get("prompt_tokens")
        obj["tokens_out"] = usage.get("completion_tokens")
        obj["ms"] = round((time.perf_counter() - _t0) * 1000)
        law_cited = law_cited_for(req["kind"], own_law, shared_law)
        if tags is not None:
            apply_v3_grade(obj, req["comment_id"], req["text"], tags, law_cited)
        finalize_record(obj, req["comment_id"], False, law_cited=law_cited)
        obj["scored_via"] = req["scored_via"]
        obj["exemplar_id"] = req["exemplar_id"]
        obj["instrument_version"] = req["instrument_version"]
        if json_dir is not None and obj["scored_via"] == "direct":
            score_json.write(json_dir, json_record(obj, model_of(args.model)))
        return obj

    stop = threading.Event()
    fatal = []

    def worker():
        # Pull from the shared queue until empty; the proxy load-balances each request
        # across the boxes, so every worker just hits the one endpoint.
        while not stop.is_set():
            try:
                req = queue.get_nowait()
            except Empty:
                return
            try:
                obj = score_job(req)
                with lock:
                    results.append(obj)
            except EndpointNotReady as exc:
                # The endpoint is scaled to zero: every remaining item fails
                # identically. Stop the run instead of grinding the queue.
                with lock:
                    if not fatal:
                        fatal.append(str(exc))
                stop.set()
                return
            except Exception as exc:
                with lock:
                    errors.append({"comment_id": req["comment_id"], "error": str(exc)})
                print(f"  ERROR {req['comment_id']} -> {exc}", flush=True)
            with lock:
                done[0] += 1
                d = done[0]
                if d % CHECKPOINT_EVERY == 0 or d == total:
                    print(f"  {d}/{total} (ok {len(results)}, err {len(errors)})", flush=True)
                # Checkpoint so a long run is crash-safe + peekable; snapshot
                # under the lock, write outside it. On the SAME interval the
                # progress line prints on, so what the run says it has done and
                # what survives an interrupt are the same number. (At 250 an
                # interrupted local run once threw away everything it had
                # scored.)
                snapshot = list(results) if d % CHECKPOINT_EVERY == 0 else None
            if snapshot is not None:
                write_outputs(snapshot)

    _run_t0 = time.perf_counter()
    threads = []
    for _ in range(args.concurrency):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        threads.append(t)
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        # Ctrl-C must not discard captured model output: stop handing out new
        # work, let in-flight calls land, and write what completed.
        stop.set()
        print("\ninterrupted — no new calls; waiting for in-flight ones, then"
              " writing what completed", flush=True)
        for t in threads:
            t.join(timeout=args.timeout)
    _elapsed = time.perf_counter() - _run_t0

    write_outputs(results)
    if fatal:
        raise SystemExit(f"ABORTED after {done[0]}/{total} items"
                         f" ({len(results)} written): {fatal[0]}")

    n = len(results)
    if n == 0:
        print(f"\n=== 0 scored, {len(errors)} errors ===")
        for e in errors:
            print("  ERROR", e["comment_id"], "->", e["error"])
        raise SystemExit("All scoring calls failed — see errors above.")
    gate_true = sum(1 for r in results if r.get("gate"))
    mism = sum(1 for r in results if r.get("strength_reported") != r["strength_check"])
    by_via = {}
    for r in results:
        by_via[r["scored_via"]] = by_via.get(r["scored_via"], 0) + 1
    print(f"\n=== scored {n} ok, {len(errors)} errors ===")
    print("by provenance: " + ", ".join(f"{k} {v}" for k, v in sorted(by_via.items())))
    print(f"gate=true (mechanical): {gate_true} ({100*gate_true/n:.1f}%)")
    print(f"model strength != sum (drift, we use the sum): {mism}")
    if by_via.get("exemplar") or by_via.get("delta"):
        print("exemplar/delta results are PARTS — run assemble_scores.py to write"
              " member rows into substance_scores.")
    # Token + throughput accounting — the basis for the cost/time estimate on the
    # Substance page. Throughput is MEASURED (n / wall-clock), so it already reflects
    # this run's concurrency.
    tin = [r["tokens_in"] for r in results if r.get("tokens_in") is not None]
    tout = [r["tokens_out"] for r in results if r.get("tokens_out") is not None]
    rate = n / _elapsed if _elapsed > 0 else 0.0
    # Local and cloud are different models on different hardware with different billing,
    # so their throughput/token stats are NOT interchangeable — persist per mode. A run
    # is homogeneous (the local box, or one remote endpoint). A remote endpoint is one the
    # client authenticates to, the same test spend_line uses.
    mode = "cloud" if client._headers else "local"
    stats = {
        "mode": mode, "n": n, "elapsed_s": round(_elapsed, 1),
        "comments_per_s": round(rate, 4),
        "concurrency": args.concurrency, "endpoints": 1,
        "avg_tokens_in": round(sum(tin) / len(tin), 1) if tin else None,
        "avg_tokens_out": round(sum(tout) / len(tout), 1) if tout else None,
    }
    # A --merged run is not the corpus's throughput: its texts are the attachments'
    # length, so its stats would skew the Substance page's estimate. Printed, not stored.
    if not args.merged:
        with db.connect(**ctx.db_config) as conn:
            conn.execute(ctx.render_sql(
                "INSERT INTO {analysis}.substance_artifacts (kind, payload) VALUES (?, ?) "
                "ON CONFLICT (kind) DO UPDATE SET payload = EXCLUDED.payload,"
                " loaded_at = CURRENT_TIMESTAMP"),
                (f"run_stats_{mode}", json.dumps(stats)))
            conn.commit()
    if tin:
        print(f"tokens: avg {sum(tin)/len(tin):.0f} in / {sum(tout)/len(tout):.0f} out per comment"
              f" over {len(tin)} calls (total {sum(tin):,} in / {sum(tout):,} out)")
    print(f"throughput: {n} comments in {_elapsed:.0f}s = {rate:.2f}/s "
          f"({rate*60:.0f}/min) across {args.concurrency} workers")
    n_direct = by_via.get("direct", 0)
    n_parts = n - n_direct
    if args.merged:
        print(f"upserted {n_direct} score(s) to {ctx.analysis_schema}.{table}")
        if errors:
            print(f"\n{len(errors)} error(s), all of them:")
            for e in errors:
                print("  ERROR", e["comment_id"], "->", e["error"])
        next_steps(
            *([(f"uv run python scripts/substance/score_comments.py --project {ctx.slug}"
                " --merged", "the queue is incremental; a re-run scores only what is"
                             " still missing.")] if args.limit or errors else []),
            ("SELECT * FROM " + f"{ctx.analysis_schema}.v_merged_score_review"
             " ORDER BY merged_strength - coalesce(own_strength, 0) DESC;",
             "each comment's own score beside its merged score."))
        return
    print(f"upserted {n_direct} score(s) to {ctx.analysis_schema}.substance_scores"
          f" and {n_parts} exemplar/delta part(s) to substance_score_parts"
          f" + run_stats_{mode}")
    if errors:
        print(f"\n{len(errors)} error(s), all of them:")
        for e in errors:
            print("  ERROR", e["comment_id"], "->", e["error"])

    cmd = "make score-model"
    steps = []
    if args.limit or errors:
        why = []
        if args.limit:
            why.append(f"--limit {args.limit} capped this run")
        if errors:
            why.append(f"{len(errors)} item(s) errored and wrote no row")
        steps.append((cmd, " and ".join(why) + " — the queue is incremental, so a"
                           " re-run scores only what is still missing."))
    if n_parts and not args.limit:
        steps.append(("make assemble",
                      "the campaign members' rows are derived from those"
                      " exemplar/delta parts and are not written yet."))
    steps.append(("make rate",
                  f"rate every eligible comment under instrument"
                  f" {args.instrument}; the ledger and the reports read that run."))
    next_steps(*steps)


if __name__ == "__main__":
    main()
