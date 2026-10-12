#!/usr/bin/env python3
"""Populate comment_group / comment_group_member — the explicit duplicate map.

Writes down, once, the answer that v_substance_representative currently derives
by walking up to six hops of recursive CTE on every query.

Runs BEFORE scoring (make groups, after make floor): the scoring
queue is one call per group's analysis carrier, decided here from the floor
survivors, so the partition depends on dedup and the floor only — never on
substance_scores.

    python scripts/substance/build_comment_groups.py --project roadless
    python scripts/substance/build_comment_groups.py --project roadless --write
    python scripts/substance/build_comment_groups.py --project roadless --rebuild --write

Dry run by default: it decides the delta (or, with --rebuild, builds the
whole partition) in memory, verifies it, and prints what it would write.

TWO PATHS:

  --write            the incremental step. The stored families persist and grow:
                     families_incremental.Increment attaches what arrived,
                     founds new families, raises the touched families'
                     counts, and the partition is re-derived in memory and
                     written as a diff keyed on group_key, so a family_id
                     and a group_id are stable across runs.
  --rebuild --write  every family from nothing (families.build), every table
                     truncated, every id reissued. Needed after a rule or
                     n-gram rebuild.

A LETTER IS ONE GROUP, and a group is one relation's class — never a chain.

A comment goes to the group it shares the most text with, tried in this order,
each over the WHOLE corpus:

  family     the same text family (families.build): copies and near-copies
             of one letter, exact classes and detector groups as cores,
             truncated and extended copies attached by containment, and every
             comment whose body is a family member's body. Kind `campaign` at
             CAMPAIGN_MIN_COMMENTS comments, `family` below; scored alike.
  middle     the same body — the text minus its last 50 characters
             (comment_dedup's middle content; a copy's body is its original's)
             — when the body class holds more than one text
  exact      identical comment_dedup.content_hash — byte identity

A class with 2+ comments is a group; everything else is a singleton, its own
canonical. The order is family, middle, exact, because each layer claims whole
classes: exact first would make a letter's exact classes separate groups and
leave the family the leftovers, copies of a letter counted as unique comments.
verify() refuses a partition in which
a family or a body class spans two groups. Membership is TOTAL, so
consumers never branch on "is this one deduplicated". Every group whose
members are in a family carries that family_id — an exact class of 3+ is
its own family, and family_id is what makes its carrier's queue item an
exemplar rather than a unique.

The families are grown or built here too, in the same run, and written in the same
transaction as the partition, so the two can never describe different
corpora.

TWO WAYS TO GET THIS WRONG, in opposite directions:

1. Precedence over LEFTOVERS. A layer computed only over comments not yet
   assigned lets `exact` claim most of a middle class, shrink the remainder
   below 2 and strand it as singletons: a comment called unique while another
   is byte-identical to it. So each class is sized over all comments, and only
   then are the already-assigned removed.

2. Union-find across the layers. A closure over the layers hops between
   them: a comment can be byte-identical to A while its header-stripped body
   matches an unrelated family B, and the closure then joins A and B into one
   group far larger than any single class. That does not make A and B the same
   comment, and one canonical cannot speak for both.

Over-merging is the dangerous direction: a canonical carries the group's
analysis forward, so a wrong merge puts words in people's mouths, while a
missed merge only costs a duplicate call. When the two errors are not
symmetric, prefer the cheap one.

The old view chains, capped at 6 hops — that cap is what stops its own runaway,
not a definition of sameness. Matching it is therefore NOT the goal, and the
verify step reports the comparison rather than demanding agreement.

CANONICAL is first presence: earliest received_date, ties broken by
comment_id. Deterministic and independent of the order anything was scored in.
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[2]))
sys.path.insert(0, str(_HERE.parent))

from shared import db  # noqa: E402
from shared.project_context import add_project_argument, context_from_args  # noqa: E402
import families as fam_mod  # noqa: E402
import families_incremental as fam_inc  # noqa: E402
from shared_text import CAMPAIGN_MIN_COMMENTS  # noqa: E402


def _step(msg):
    """Progress to stdout. The clustering below takes minutes on a full corpus
    and printed nothing until it was done, so a run looked hung."""
    print(msg, flush=True)


def load_comments(conn, ctx):
    """(first_seen, dedup_rows): every comment's received_date, and every
    comment_dedup row as (content_hash, middle_content_hash,
    original_comment_id, is_original, duplicate_group_size)."""
    _step("loading comments...")
    first_seen = {cid: rd for cid, rd in conn.execute(ctx.render_sql(
        "SELECT comment_id, received_date FROM {analysis}.v_source_comments"))}
    _step(f"  {len(first_seen):,} comments")
    dedup_rows = {}
    for cid, ch, mh, orig, is_orig, size in conn.execute(ctx.render_sql(
            "SELECT comment_id, content_hash, middle_content_hash, original_comment_id,"
            " is_original, duplicate_group_size FROM {analysis}.comment_dedup")):
        dedup_rows[cid] = (ch, mh, orig, is_orig, size)
    _step(f"  {len(dedup_rows):,} dedup rows")
    return first_seen, dedup_rows


def build(conn, ctx):
    """The whole partition from a full family build, in memory. Returns
    (groups, members, stats, families, weight): the partition and the
    families it was built on, so --rebuild --write stores both from one
    build."""
    first_seen, dedup_rows = load_comments(conn, ctx)
    _step("building the text families (minutes on a full corpus)...")
    families, review, weight, survivors = fam_mod.build(conn, ctx)
    groups, member_rows, stats = assemble(first_seen, dedup_rows, families, weight,
                                          survivors, len(review))
    return groups, member_rows, stats, families, weight


def assemble(first_seen, dedup_rows, families, weight, survivors, n_review=0):
    """The partition over these families, in memory: (groups, member_rows,
    stats). The families are objects with family_id, members (comment id ->
    Member with has_own_text and shared_chars), exemplar_id and
    n_comments(weight); a full build's and the incremental step's alike."""
    _t0 = time.time()
    dedup, dedup_original = {}, {}
    for cid, (ch, mh, orig, _is_orig, _size) in dedup_rows.items():
        dedup[cid] = (ch, mh)
        dedup_original[cid] = orig or cid

    # The relation each pair of comments is joined by, kept so group_kind can
    # name the strongest one present in a component.
    rel = {}                                       # comment_id -> {relations}

    # A LETTER IS ONE GROUP. A comment goes to the group it shares the most text
    # with: its text family first (families.build — shared text by length,
    # share of the comment and how often it repeats), then its body class, then
    # its exact class. The order matters because each layer claims whole
    # classes: with exact first, every exact class of a letter would become its
    # own group and the family would keep only the leftovers.
    #
    # Still NO CHAINING. Each group is one relation's class: a family, or a
    # body class, or an exact class. An exact class lies inside exactly one
    # body class (a copy's body is its original's), and a body class that
    # touches a family goes into that family whole — its members share the
    # family's text by construction. A body class touching two families cannot
    # be placed and stops the build (_body_family below).
    #
    # The body is comment_dedup's middle content: the text minus its last 50
    # characters, too short to carry substance. comment_dedup stores it on the
    # full-text original only; a copy's body is its original's.
    def body_of(cid):
        return dedup.get(dedup_original.get(cid, cid), (None, None))[1]

    bodies = defaultdict(list)
    for cid in dedup:
        if cid in first_seen and body_of(cid):
            bodies[body_of(cid)].append(cid)

    # A family's members are TEXTS (one original per exact class); the
    # partition works in comments, so each member text stands for its whole
    # exact class here. family_of names every comment's family.
    copies = defaultdict(list)
    for cid, (_ch, _mh) in dedup.items():
        copies[dedup_original.get(cid, cid)].append(cid)
    family_of, member_of = {}, {}
    fam_by_id = {fam.family_id: fam for fam in families}
    for fam in families:
        for text_id, member in fam.members.items():
            for cid in copies.get(text_id, [text_id]):
                family_of[cid] = fam
                member_of[cid] = member
    # A body class that touches a family joins it whole: a comment whose body
    # is a family member's body shares that family's text.
    for bh, cids in bodies.items():
        fams = {family_of[c].family_id for c in cids if c in family_of}
        if len(fams) > 1:
            raise SystemExit(
                f"body class {bh} touches families {sorted(fams)} — one body cannot"
                " be two letters; the family build and the middle-content dedup disagree")
        if fams:
            fam = fam_by_id[next(iter(fams))]
            for c in cids:
                family_of.setdefault(c, fam)
    layers: dict[str, dict[str, list[str]]] = {"family": defaultdict(list)}
    for cid, fam in family_of.items():
        if cid in first_seen:
            layers["family"][fam.family_id].append(cid)
    # A body class of one text is an exact class; it is a middle group only
    # when it holds more than one text.
    layers["middle"] = {bh: cids for bh, cids in bodies.items()
                        if len({dedup[c][0] for c in cids}) > 1}
    layers["exact"] = defaultdict(list)
    for cid, hashes in dedup.items():
        if hashes[0] and cid in first_seen:
            layers["exact"][hashes[0]].append(cid)
    _step(f"  {len(families):,} families over {len(family_of):,} comments;"
          f" {len(layers['middle']):,} multi-text body classes;"
          f" {sum(1 for v in layers['exact'].values() if len(v) > 1):,} exact classes with 2+")
    _step("assigning every comment to the letter it shares the most text with...")

    assigned = {}
    comps = defaultdict(list)
    for kind in ("family", "middle", "exact"):
        for key, cids in layers[kind].items():
            live = [c for c in cids if c in first_seen]
            if len(live) < 2:
                continue
            # Membership is decided by the FULL class, not by what is left
            # over: the first version filtered to unassigned comments first,
            # which shrank a middle class below 2 and stranded its remainder
            # as singletons despite having real duplicates.
            take = [c for c in live if c not in assigned]
            if not take:
                continue
            if kind == "family":
                fam = fam_by_id[key]
                kind_out = ("campaign" if fam.n_comments(weight) >= CAMPAIGN_MIN_COMMENTS
                            else "family")
            else:
                kind_out = kind
            for c in take:
                assigned[c] = (kind_out, key)
                rel.setdefault(c, set()).add(kind_out)
            comps[(kind_out, key)].extend(take)
    for cid in first_seen:
        if cid not in assigned:
            comps[("singleton", cid)].append(cid)

    # own text: did this member contribute anything beyond the group's shared
    # content? A singleton's text is entirely its own. Otherwise it is the
    # family attribution's answer where it has one (families.attribute, with
    # the trivial-own rule) — a comment in no family, or outside the survivor
    # population, has no measurement, which is False rather than a guess.
    def own(cid, kind):
        if kind == "singleton":
            return True
        m = member_of.get(cid)
        return bool(m and m.has_own_text)

    def analysis_carrier(kind, cids, canonical):
        """The member of THIS group whose text the scoring queue sends, or
        None when no member survived the floor filter.

        Decided HERE, before scoring, so the queue (score_comments.py), the
        assembler (assemble_scores.py) and the pages all name the same comment
        per group, and the partition never depends on the scorer.

        family,   the family's exemplar when it survived the floor — the
        campaign  most-copied text, or the one nearest the whole family; else
                  the surviving member with the most shared text. The queue
                  sends its SHARED text once for the whole family; the other
                  members inherit.
        others    the canonical, when it survived the floor. The floor runs on
                  comment_dedup's original (lowest id) and first presence is
                  not always that comment, so a canonical can have no floor
                  row; then the lowest-id surviving member, whose text is the
                  same (exact) or the same body (middle).
        None      no member survived: nothing to score, nothing to point at.
                  The deferred FK comment_group_analysis_is_member lets the
                  NULL through and rejects any non-member.
        """
        alive = [c for c in cids if c in survivors]
        if not alive:
            return None
        if kind in ("family", "campaign"):
            fam = family_of[cids[0]]
            if fam.exemplar_id in alive:
                return fam.exemplar_id
            # A body-class comment joined to the family has no Member row of
            # its own (it is not a family text); it ranks last.
            return max(sorted(alive),
                       key=lambda c: (member_of[c].shared_chars or 0) if c in member_of else -1)
        return canonical if canonical in survivors else min(alive)

    groups, member_rows = [], []
    for (kind, _layer_key), cids in comps.items():
        canonical = min(cids, key=lambda c: (first_seen[c], c))
        key = canonical                            # the group's stable name
        fams = {family_of[c].family_id for c in cids if c in family_of}
        if len(fams) > 1:
            raise SystemExit(
                f"group {kind}/{key} spans families {sorted(fams)} — a hash class"
                " is one text or one body and cannot be in two families")
        groups.append({"group_kind": kind, "group_key": key,
                       "canonical_comment_id": canonical, "size": len(cids),
                       "analysis_comment_id": analysis_carrier(kind, cids,
                                                               canonical),
                       "family_id": next(iter(fams)) if fams else None,
                       "first_seen_at": first_seen[canonical]})
        for cid in cids:
            member_rows.append({"comment_id": cid, "kind": kind, "key": key,
                                "has_own_text": own(cid, kind)})

    stats = defaultdict(int)
    for g in groups:
        stats[g["group_kind"]] += 1
        stats[g["group_kind"] + "_members"] += g["size"]
    stats["comments"] = len(first_seen)
    stats["no_dedup_row"] = sum(1 for c in first_seen if c not in dedup)
    stats["with_family"] = sum(1 for g in groups if g["family_id"] is not None)
    stats["review"] = n_review
    _step(f"built {len(groups):,} groups over {len(member_rows):,} members"
          f" in {time.time() - _t0:.0f}s\n")
    return groups, member_rows, stats


def verify(conn, ctx, groups, member_rows, families=(), weight=None, old_view=True):
    """Fail loudly rather than write a partition that is wrong. The
    comparison against v_substance_representative runs only with old_view:
    that view is a 6-hop recursive CTE over the whole corpus and takes minutes,
    which is the cost of a full check, not of the incremental step. The rebuild
    pays it; the incremental delta verifies the
    in-memory invariants and the over-merge bound is what the partition's
    own rule (one hash class, never a chain) already guarantees."""
    problems = []
    seen = {}
    for m in member_rows:
        if m["comment_id"] in seen:
            problems.append(f"{m['comment_id']} in two groups")
        seen[m["comment_id"]] = (m["kind"], m["key"])
    # The family invariants: every family_id names a family of this build; a family or
    # campaign group has one; a campaign group's family has
    # CAMPAIGN_MIN_COMMENTS comments; a family carrier is the exemplar when
    # the exemplar survived.
    fam_by_id = {f.family_id: f for f in families}
    for g in groups:
        fid = g["family_id"]
        if fid is not None and fid not in fam_by_id:
            problems.append(f"group {g['group_kind']}/{g['group_key']} names family"
                            f" {fid}, which this build did not produce")
        if g["group_kind"] in ("family", "campaign"):
            if fid is None:
                problems.append(f"group {g['group_kind']}/{g['group_key']} has no family_id")
            elif weight is not None:
                n = fam_by_id[fid].n_comments(weight)
                if (g["group_kind"] == "campaign") != (n >= CAMPAIGN_MIN_COMMENTS):
                    problems.append(f"group {g['group_kind']}/{g['group_key']}: family"
                                    f" {fid} has {n} comments, the wrong label")
    # A LETTER IS ONE GROUP (assemble). A family on two groups, or a body class
    # on two groups, is a letter counted as several unique comments. Checked on every build.
    groups_of_family = defaultdict(set)
    for g in groups:
        if g["family_id"] is not None:
            groups_of_family[g["family_id"]].add((g["group_kind"], g["group_key"]))
    split_fams = {f: ks for f, ks in groups_of_family.items() if len(ks) > 1}
    if split_fams:
        problems.append(
            f"{len(split_fams)} family(ies) split across groups — a letter counted as"
            " several unique comments:" + "".join(
                f"\n      family {f}: {len(ks)} groups" for f, ks in sorted(
                    split_fams.items(), key=lambda kv: -len(kv[1]))[:20]))
    groups_of_body = defaultdict(set)
    for cid, body in conn.execute(ctx.render_sql(
            "SELECT d.comment_id, coalesce(d.middle_content_hash, o.middle_content_hash)"
            " FROM {analysis}.comment_dedup d"
            " LEFT JOIN {analysis}.comment_dedup o ON o.comment_id = d.original_comment_id")):
        if body and cid in seen:
            groups_of_body[body].add(seen[cid])
    split_bodies = {b: ks for b, ks in groups_of_body.items() if len(ks) > 1}
    if split_bodies:
        problems.append(
            f"{len(split_bodies)} body class(es) split across groups — one text minus"
            " its last 50 characters counted as several unique comments:" + "".join(
                f"\n      body {b}: {len(ks)} groups" for b, ks in sorted(
                    split_bodies.items(), key=lambda kv: -len(kv[1]))[:20]))

    total = {c for (c,) in conn.execute(ctx.render_sql(
        "SELECT comment_id FROM {analysis}.v_source_comments"))}
    missing = total - set(seen)
    if missing:
        problems.append(f"{len(missing)} comment(s) in no group")
    by_key = {(g["group_kind"], g["group_key"]): g for g in groups}
    counted = defaultdict(int)
    for m in member_rows:
        counted[(m["kind"], m["key"])] += 1
    for k, g in by_key.items():
        if counted[k] != g["size"]:
            problems.append(f"group {k} size {g['size']} != {counted[k]} members")
        if seen.get(g["canonical_comment_id"]) != k:
            problems.append(f"group {k} canonical is not one of its members")
        # comment_group_analysis_is_member is DEFERRABLE INITIALLY DEFERRED, so
        # a bad value returns success on INSERT and raises only at COMMIT, by
        # which point the failure names a constraint rather than a group. Catch
        # it here where the group can be named.
        acid = g["analysis_comment_id"]
        if acid is not None and seen.get(acid) != k:
            problems.append(f"group {k} analysis_comment_id {acid} is not one"
                            " of its members")

    # THE OLD-VIEW CHECK — grouping agreement, not representative agreement.
    #
    # Comparing chosen representatives is the wrong test and it fails for
    # reasons that are not defects: many of the old view's rows resolve to
    # SELF, and its chain deliberately steps over floored comments because it
    # resolves to a SCORABLE representative. Ours is first presence. Both are
    # legitimate; they are answers to different questions.
    #
    # What must hold is that both agree on WHICH COMMENTS ARE THE SAME. For
    # every comment the old view resolves to something other than itself, that
    # something must be in the same group here. A single disagreement means the
    # closure differs and the new table cannot replace the view.
    if not old_view:
        return problems, 0, 0
    old_pairs = [(cid, rep) for cid, rep in conn.execute(ctx.render_sql(
        "SELECT comment_id, rep_comment_id"
        " FROM {analysis}.v_substance_representative")) if cid != rep]
    agree = differ = 0
    for cid, rep in old_pairs:
        if seen.get(cid) is not None and seen.get(cid) == seen.get(rep):
            agree += 1
        else:
            differ += 1
    # Reported, NOT enforced. The old view chains across hash layers to a
    # 6-hop cap; this builder deliberately does not chain at all, so a
    # disagreement here is the designed difference, not a defect. What IS
    # enforced is the over-merge bound below: no group may contain comments
    # the old view resolves to more than one distinct representative, because
    # that is the direction where a canonical would speak for people it does
    # not represent.
    # Bounded on the HASH groups only. A family or campaign group holds every
    # variant of one letter by the family build's thresholds (length, share and
    # repetition of the shared text); the old view never saw families, so it
    # splits a campaign's personalized variants across as many reps as there are
    # variants. That is the letter being
    # one group, not an over-merge.
    by_group = defaultdict(set)
    for cid, rep in old_pairs:
        if seen.get(cid) is not None and seen[cid][0] in ("exact", "middle"):
            by_group[seen[cid]].add(rep)
    overmerged = {k: len(v) for k, v in by_group.items() if len(v) > 1}
    if overmerged:
        by_worst = sorted(overmerged.items(), key=lambda kv: -kv[1])
        problems.append(
            f"{len(overmerged)} group(s) contain comments the old view splits"
            f" across several reps — over-merge. All of them, worst first:"
            + "".join(f"\n      {k}: {n} reps" for k, n in by_worst))
    return problems, agree, differ


def report(groups, member_rows, stats, n_families, agree, differ, old_view):
    print(f"comments: {stats['comments']}"
          f"  ({stats['no_dedup_row']} with no comment_dedup row)")
    for kind in ("exact", "middle", "family", "campaign", "singleton"):
        print(f"  {kind:<10} {stats[kind]:>7} groups"
              f"  {stats[kind + '_members']:>7} members")
    print(f"total: {len(groups)} groups, {len(member_rows)} member rows;"
          f" {stats['with_family']} groups carry a family_id;"
          f" {n_families} families; {stats['review']} middle class(es) on the"
          " review list (families.py prints them)")
    print(f"UNIQUE COMMENTS: {len(groups):,} of {stats['comments']:,} collected"
          " (one per comment group — the reported figure)")
    if old_view:
        print(f"closure vs v_substance_representative:"
              f" {agree} same group, {differ} different")

    # The carrier differs from the canonical for family and campaign
    # groups (the exemplar) and for exact/middle groups whose
    # first-presence canonical has no floor row. Printed per kind so a
    # move names which kind moved.
    print("analysis carrier vs canonical:")
    for kind in ("exact", "middle", "family", "campaign", "singleton"):
        of_kind = [g for g in groups if g["group_kind"] == kind]
        differs = sum(1 for g in of_kind
                      if g["analysis_comment_id"] is not None
                      and g["analysis_comment_id"] != g["canonical_comment_id"])
        none_ = sum(1 for g in of_kind if g["analysis_comment_id"] is None)
        print(f"  {kind:<10} {len(of_kind):>7} groups"
              f"  {differs:>6} differ  {none_:>6} no carrier")


def write_full(cur, ctx, groups, member_rows, families, weight):
    """The rebuild's write: every family and group table emptied and
    reinserted, in the caller's transaction. Ids are reissued."""
    # Families and the partition in ONE transaction: comment_group
    # .family_id names a family of the same build, and neither table
    # can describe a corpus the other does not.
    for table in ("text_family_span", "text_family_member", "text_family_sentence",
                  "text_family_ngram", "text_family", "comment_group_member", "comment_group"):
        cur.execute(ctx.render_sql("DELETE FROM {analysis}." + table))
    family_ids = fam_mod.write(cur, ctx, families, weight)
    cur.executemany(ctx.render_sql(
        "INSERT INTO {analysis}.comment_group"
        " (group_kind, group_key, canonical_comment_id,"
        "  analysis_comment_id, size, first_seen_at, family_id)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)"),
        [(g["group_kind"], g["group_key"], g["canonical_comment_id"],
          g["analysis_comment_id"], g["size"], g["first_seen_at"],
          family_ids[g["family_id"]] if g["family_id"] is not None else None)
         for g in groups])
    ids = {(k, key): gid for gid, k, key in cur.execute(ctx.render_sql(
        "SELECT group_id, group_kind, group_key"
        " FROM {analysis}.comment_group")).fetchall()}
    cur.executemany(ctx.render_sql(
        "INSERT INTO {analysis}.comment_group_member"
        " (comment_id, group_id, has_own_text) VALUES (?, ?, ?)"),
        [(m["comment_id"], ids[(m["kind"], m["key"])],
          m["has_own_text"]) for m in member_rows])


def partition_delta(stored_groups, stored_members, groups, member_rows, family_ids):
    """What the incremental write changes in the two group tables, keyed on
    group_key: a group's key is its earliest member, so a group that
    persists keeps its group_id whatever its kind or size became.
    stored_groups: {key: (group_id, kind, canonical, analysis, size,
    family_id)}; stored_members: {comment_id: (group_id, has_own_text)}.
    Returns (inserts, updates, deletes, member_rows_changed): groups to
    insert, (group_id, fields) to update, group ids to delete, and the
    (comment_id, key, has_own_text) rows whose group or flag changed."""
    inserts, updates = [], []
    desired = {}
    for g in groups:
        fid = family_ids[g["family_id"]] if g["family_id"] is not None else None
        row = (g["group_kind"], g["canonical_comment_id"], g["analysis_comment_id"],
               g["size"], fid, g["first_seen_at"])
        desired[g["group_key"]] = row
        stored = stored_groups.get(g["group_key"])
        if stored is None:
            inserts.append((g["group_key"],) + row)
        elif stored[1:] != row[:5]:
            updates.append((stored[0],) + row)
    deletes = [gid for key, (gid, *_rest) in stored_groups.items() if key not in desired]
    key_of_gid = {gid: key for key, (gid, *_rest) in stored_groups.items()}
    changed = []
    for m in member_rows:
        stored = stored_members.get(m["comment_id"])
        if stored is None or key_of_gid.get(stored[0]) != m["key"] \
                or stored[1] != m["has_own_text"]:
            changed.append((m["comment_id"], m["key"], m["has_own_text"]))
    return inserts, updates, deletes, changed


def write_delta(cur, ctx, groups, member_rows, family_ids):
    """The incremental write of the partition: insert the new groups, update the
    changed ones, move the members that moved, delete the groups nothing is
    in any more. Returns the counts as (inserted, updated, deleted,
    members_changed)."""
    stored_groups = {key: (gid, kind, canon, acid, size, fid) for gid, kind, key, canon, acid,
                     size, fid in cur.execute(ctx.render_sql(
                         "SELECT group_id, group_kind, group_key, canonical_comment_id,"
                         " analysis_comment_id, size, family_id"
                         " FROM {analysis}.comment_group")).fetchall()}
    stored_members = {cid: (gid, own) for cid, gid, own in cur.execute(ctx.render_sql(
        "SELECT comment_id, group_id, has_own_text"
        " FROM {analysis}.comment_group_member")).fetchall()}
    inserts, updates, deletes, changed = partition_delta(
        stored_groups, stored_members, groups, member_rows, family_ids)
    gid_of_key = {key: gid for key, (gid, *_rest) in stored_groups.items()}
    for row in inserts:
        got = cur.execute(ctx.render_sql(
            "INSERT INTO {analysis}.comment_group"
            " (group_key, group_kind, canonical_comment_id, analysis_comment_id, size,"
            "  family_id, first_seen_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
            " RETURNING group_id"), row).fetchone()
        assert got is not None
        gid_of_key[row[0]] = got[0]
    cur.executemany(ctx.render_sql(
        "UPDATE {analysis}.comment_group SET group_kind = ?, canonical_comment_id = ?,"
        " analysis_comment_id = ?, size = ?, family_id = ?, first_seen_at = ?,"
        " built_at = CURRENT_TIMESTAMP WHERE group_id = ?"),
        [(kind, canon, acid, size, fid, seen, gid)
         for gid, kind, canon, acid, size, fid, seen in updates])
    cur.executemany(ctx.render_sql(
        "INSERT INTO {analysis}.comment_group_member (comment_id, group_id, has_own_text)"
        " VALUES (?, ?, ?) ON CONFLICT (comment_id) DO UPDATE"
        " SET group_id = EXCLUDED.group_id, has_own_text = EXCLUDED.has_own_text"),
        [(cid, gid_of_key[key], own) for cid, key, own in changed])
    if deletes:
        cur.execute(ctx.render_sql(
            "DELETE FROM {analysis}.comment_group WHERE group_id IN (SELECT value FROM json_each(?))"), (json.dumps(deletes),))
    return len(inserts), len(updates), len(deletes), len(changed)


def main() -> None:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    add_project_argument(p)
    p.add_argument("--write", action="store_true",
                   help="apply (default: build, verify and report only)")
    p.add_argument("--rebuild", action="store_true",
                   help="rebuild every family from nothing and reissue every family and"
                        " group id (default: grow the stored families by what arrived)")
    args = p.parse_args()
    ctx = context_from_args(args)

    with db.connect(**ctx.db_config) as conn:
        if args.rebuild:
            groups, member_rows, stats, families, weight = build(conn, ctx)
            increment = None
        else:
            first_seen, dedup_rows = load_comments(conn, ctx)
            increment = fam_inc.Increment(conn, ctx, first_seen, dedup_rows).compute()
            families = increment.current_families()
            weight = increment.weight
            groups, member_rows, stats = assemble(first_seen, dedup_rows, families, weight,
                                                  increment.survivors, len(increment.merges))
        print("verifying (every comment in exactly one group, sizes, carriers, families"
              + (", over-merge bound)..." if args.rebuild else ")..."), flush=True)
        problems, agree, differ = verify(conn, ctx, groups, member_rows, families, weight,
                                         old_view=args.rebuild)
        report(groups, member_rows, stats, len(families), agree, differ, args.rebuild)
        if increment is not None:
            increment.report()

        if problems:
            for pr in problems:
                print("  PROBLEM:", pr)
            raise SystemExit(f"{len(problems)} verification problem(s) —"
                             " nothing written.")

        if not args.write:
            print("\nDry run — nothing written. Re-run with --write to apply.")
            return

        with conn.cursor() as cur:
            cur.execute("PRAGMA defer_foreign_keys = ON")
            if increment is None:
                write_full(cur, ctx, groups, member_rows, families, weight)
                conn.commit()
                print(f"\nrebuilt: wrote {len(families)} families and {len(groups)} groups,"
                      f" {len(member_rows)} members. Every family and group id is new.")
                return
            family_ids = increment.write(cur)
            n_ins, n_upd, n_del, n_mem = write_delta(cur, ctx, groups, member_rows, family_ids)
        conn.commit()
        print(f"\nwrote the delta: {len(increment.new_families)} new families,"
              f" {len(increment.merges)} merges, {increment.stats['new_member_rows']} new"
              f" member rows, {increment.stats['reattributed']} attributions,"
              f" {increment.stats['distinctive_refreshed']} distinctive flags refreshed;"
              f" groups: {n_ins} inserted, {n_upd} updated, {n_del} deleted,"
              f" {n_mem} member rows changed.")


if __name__ == "__main__":
    main()
