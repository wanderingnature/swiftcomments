#!/usr/bin/env python3
"""The incremental family step: stored families persist and grow, new texts
attach to them or found new ones, and only what changed is written, in place
of a rebuild of every family from nothing with fresh ids. This module
is the other path build_comment_groups.py --write takes when --rebuild is
not given:

  copies       a new comment that is a copy of a known text changes no
               membership: its text's weight grows, and if that text is a
               core text its n-gram and sentence counts grow by the copies.
  cores        a new text in a detector group whose texts are core members
               of a stored family joins that family as core (the core floor
               applies); a middle class does the same, and a class or group
               spanning two stored families merges the younger into the
               older. A group, class or original with no family and
               FAMILY_MIN_COMMENTS comments is a new family.
  attach       every new text still in no family is offered to the
               distinctive n-grams of every family, stored and new; every
               old text in no family is offered to the new families only.
  second pass  the new texts still in no family that carry repeated
               material are grouped by containment against the old texts in
               no family, which lead and are never regrouped among
               themselves; a group of two or more texts with enough
               comments is a contain core.
  touched      a stored family that gained a core text or copies gets its
               counts raised, never recomputed: an n-gram or sentence whose
               count crosses family_text_min joins the family text, and
               only the members that carry it are re-attributed.

Nothing is undone: an attachment is permanent, the exemplar is chosen once,
a family's count never falls back under the floor. The one event that
retires a family_id is a merge, and the older id survives it. What only a
full rebuild changes is listed in the design page.

Reads the same inputs as the build and refuses to run before a rebuild has
stored the incremental state (text_family_sentence, own_sentence_keys).
"""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[2]))
sys.path.insert(0, str(_HERE.parent))

from shared.near_duplicates import SimpleBloomFilter  # noqa: E402
import families as fm  # noqa: E402
from families import Family, Member  # noqa: E402
from shared_text import (  # noqa: E402
    CAMPAIGN_MIN_COMMENTS, CONTAIN_THRESHOLD, DISTINCTIVE_SHARE, FAMILY_MIN_COMMENTS,
    MEMBERSHIP_FLOOR, SECOND_PASS_MIN_SHARED)

_CHUNK = 20000


def _step(msg):
    print(msg, flush=True)


# ------------------------------------------------------------ pure parts

class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

    def components(self):
        out = defaultdict(list)
        for x in list(self.parent):
            out[self.find(x)].append(x)
        return list(out.values())


def resolve_components(units, core_family_of, member_of):
    """Which stored family, if any, each new text joins as core, and which
    texts found a family of their own.

    units: [(kind, [texts])] — every detector group and middle class that a
    new or grown text touched. core_family_of: text -> stored family id for
    the texts that are core members; member_of: the same for every member,
    attached ones included. Units sharing a text are one component, as in
    the build (one text cannot be two letters), and a component holding
    core texts of stored families targets the oldest of them: the others
    merge into it, and the component's free texts join it. A component with
    no stored core family is a new core of its free texts when it has two
    or more of them. Attached members are never free: an attachment is
    permanent, and a family is named by its cores. An attached member pulls a
    component through one relation only, its middle class: a body class lies
    in one family in the partition (build_comment_groups refuses one that
    touches two), so a middle class holding a member attached to family F
    binds its unit to F, and a component that also holds another family's
    cores merges the younger into the older. Otherwise a new text with the
    body of a member attached to one family could be pulled by its near group
    into another, the same letter stored twice.

    Returns (joins, merges, new_cores): joins {stored fid: [free texts]},
    merges [(into, from)] with into < from, new_cores [(kind, [texts])]."""
    uf = UnionFind()
    for i, (kind, texts) in enumerate(units):
        uf.find(("unit", i))
        for t in texts:
            uf.union(("unit", i), ("text", t))
            fid = core_family_of.get(t)
            if fid is None and kind == "middle":
                fid = member_of.get(t)
            if fid is not None:
                uf.union(("unit", i), ("fam", fid))
    joins, merges, new_cores = defaultdict(list), [], []
    for comp in uf.components():
        fams = sorted(f for tag, f in comp if tag == "fam")
        unit_ids = [i for tag, i in comp if tag == "unit"]
        free = sorted({t for tag, t in comp if tag == "text" and t not in member_of})
        if fams:
            target = fams[0]
            for f in fams[1:]:
                merges.append((target, f))
            if free:
                joins[target].extend(free)
        else:
            kinds = {units[i][0] for i in unit_ids}
            kind = "near" if "near" in kinds else "middle"
            if len(free) >= 2:
                new_cores.append((kind, free))
    return dict(joins), sorted(set(merges)), new_cores


def raised_counts(counts, contributions, sets, n_min):
    """Raise a family's n-gram counts by the contributing texts' weights,
    in place. counts: {ngram: weighted count} of the family text (at or
    above n_min); contributions: {text: added comments}; sets: text ->
    n-gram set. Returns (changed, candidates): the n-grams already in the
    family text whose count rose, and {ngram: added} for the ones not in it,
    whose stored count is unknown and must be measured before they can
    cross n_min."""
    changed, candidates = set(), defaultdict(int)
    for t, dw in contributions.items():
        for ng in sets.get(t, ()):
            if ng in counts:
                counts[ng] += dw
                changed.add(ng)
            else:
                candidates[ng] += dw
    return changed, dict(candidates)


def raised_sentences(counts, contributions, keys_of, n_min):
    """Raise a family's sentence counts by the contributing texts' weights,
    in place. keys_of: text -> its sentence keys. Returns (changed, added):
    every key whose count rose, and the keys that crossed n_min now."""
    changed, added = set(), set()
    for t, dw in contributions.items():
        for k in keys_of.get(t, ()):
            old = counts.get(k, 0)
            counts[k] = old + dw
            changed.add(k)
            if old < n_min <= old + dw:
                added.add(k)
    return changed, added


def merge_counts(into, frm):
    """Sum two count maps into the first, in place."""
    for k, n in frm.items():
        into[k] = into.get(k, 0) + n


def attach_units(pending_units, index, by_id, sets):
    """The build's attach rule over these units: each joins the family whose
    distinctive n-grams cover the largest share of the unit's n-grams, at or
    above MEMBERSHIP_FLOOR. index: distinctive ngram -> family id; by_id:
    family id -> Family. Returns [(family, unit, coverage)]."""
    out = []
    for unit in pending_units:
        total = 0
        hits = defaultdict(int)
        for c in unit:
            for ng in sets.get(c, ()):
                total += 1
                fid = index.get(ng)
                if fid is not None:
                    hits[fid] += 1
        if not hits or not total:
            continue
        fid, n = max(hits.items(), key=lambda kv: (kv[1], -kv[0]))
        cov = n / total
        if cov >= MEMBERSHIP_FLOOR:
            out.append((by_id[fid], unit, cov))
    return out


def contain_against(fixed, new_items, threshold):
    """Leader assignment by containment with the old pending texts as
    leaders that are never compared among themselves: they were offered to
    each other on the run that left them pending, and the full pass over
    them is the 100 s this step exists to avoid. fixed and new_items are
    [(id, n-gram set, weight)]; new texts are visited by weight descending,
    then shortest first, then id, and each joins the leader it overlaps
    most at or above the threshold or leads. Returns [(leader, members)]
    for the leaders that gained a member, members including the leader."""
    if not new_items:
        return []
    order = sorted(new_items, key=lambda it: (-it[2], len(it[1]), it[0]))
    bloom_size = max(1024, max(len(it[1]) for it in list(fixed) + order) * 10)
    leaders = [(cid, ngrams, SimpleBloomFilter(ngrams, size=bloom_size), {cid}, False)
               for cid, ngrams, _w in fixed]
    for cid, ngrams, _w in order:
        bloom = SimpleBloomFilter(ngrams, size=bloom_size)
        best, best_overlap = None, 0.0
        for leader in leaders:
            if leader[2].containment(bloom) < threshold * 0.7:
                continue
            smaller = min(len(ngrams), len(leader[1]))
            if smaller == 0:
                continue
            overlap = len(ngrams & leader[1]) / smaller
            if overlap >= threshold and overlap > best_overlap:
                best, best_overlap = leader, overlap
        if best is None:
            leaders.append((cid, ngrams, bloom, {cid}, True))
        else:
            best[3].add(cid)
    return [(leader[0], leader[3]) for leader in leaders if len(leader[3]) >= 2]


def family_sizes(fam, weight):
    n_comments = fam.n_comments(weight)
    return len(fam.members), n_comments, n_comments >= CAMPAIGN_MIN_COMMENTS


# --------------------------------------------------------------- loading

def _chunks(ids):
    ids = sorted(ids)
    for i in range(0, len(ids), _CHUNK):
        yield ids[i:i + _CHUNK]


def fetch_texts(conn, ctx, ids):
    out = {}
    for chunk in _chunks(ids):
        for cid, text in conn.execute(ctx.render_sql(
                "SELECT comment_id, comment_text FROM {analysis}.v_source_comments"
                " WHERE comment_id IN (SELECT value FROM json_each(?))"), (json.dumps(chunk),)):
            out[cid] = text or ""
    return out


def fetch_sets(conn, ctx, ids):
    out = {}
    for chunk in _chunks(ids):
        for cid, ngs in conn.execute(ctx.render_sql(
                "SELECT comment_id, json_group_array(ngram_id) FROM {analysis}.comment_long_ngrams"
                " WHERE comment_id IN (SELECT value FROM json_each(?)) GROUP BY comment_id"), (json.dumps(chunk),)):
            out[cid] = frozenset(json.loads(ngs))
    return out


def fetch_frequency(conn, ctx, ngram_ids, cache):
    need = [ng for ng in set(ngram_ids) if ng not in cache]
    for chunk in _chunks(need):
        for ng, cf in conn.execute(ctx.render_sql(
                "SELECT ngram_id, comment_frequency FROM {analysis}.long_ngram_stats"
                " WHERE ngram_id IN (SELECT value FROM json_each(?))"), (json.dumps(chunk),)):
            cache[ng] = cf
    return cache


def fetch_occurrences(conn, ctx, ids):
    """{comment_id: [(ngram_id, start, end)]} for these texts; a text with
    no rows (under six tokens) maps to []."""
    out = {cid: [] for cid in ids}
    for chunk in _chunks(ids):
        for cid, ng, a, b in conn.execute(ctx.render_sql(
                "SELECT comment_id, ngram_id, char_start, char_end"
                " FROM {analysis}.comment_long_ngrams WHERE comment_id IN (SELECT value FROM json_each(?))"), (json.dumps(chunk),)):
            if a is None:
                raise SystemExit(
                    f"comment_long_ngrams has no offsets for {cid} — run"
                    " comments_db/scripts/extract_long_ngrams.py --rebuild first.")
            out[cid].append((ng, a, b))
    return out


def load_stored(conn, ctx):
    """Every stored family as a Family, members and counts included, plus
    the sizes as stored so a change is written only when there is one."""
    families, sizes = {}, {}
    for fid, ex, kind, n_texts, n_comments, is_campaign, n_min in conn.execute(ctx.render_sql(
            "SELECT family_id, exemplar_comment_id, core_kind, n_texts, n_comments,"
            " is_campaign, family_text_min FROM {analysis}.text_family")):
        families[fid] = Family(family_id=fid, core_kind=kind, core=[], exemplar_id=ex,
                               family_text_min=n_min)
        sizes[fid] = (n_texts, n_comments, is_campaign)
    if not families:
        raise SystemExit(
            "text_family is empty — run"
            " scripts/substance/build_comment_groups.py --rebuild --write first."
            " The incremental step grows stored families; it cannot start from none.")
    for fid, ng, n, distinctive in conn.execute(ctx.render_sql(
            "SELECT family_id, ngram_id, n_core_texts, distinctive"
            " FROM {analysis}.text_family_ngram")):
        fam = families[fid]
        fam.ngrams[ng] = n
        if distinctive:
            fam.distinctive.add(ng)
    n_sentences = 0
    for fid, key, n in conn.execute(ctx.render_sql(
            "SELECT family_id, sentence_key, n_comments FROM {analysis}.text_family_sentence")):
        families[fid].sentence_counts[key] = n
        n_sentences += 1
    if not n_sentences:
        raise SystemExit(
            "text_family_sentence is empty — the stored families predate the incremental"
            " state. Run scripts/substance/build_comment_groups.py --rebuild --write once.")
    for fam in families.values():
        fam.sentence_keys = fm.keys_at_threshold(fam.sentence_counts, fam.family_text_min)
    for (cid, fid, via, cov, shared, own, own_tokens, margin, has_own,
         own_keys) in conn.execute(ctx.render_sql(
            "SELECT comment_id, family_id, joined_via, coverage, shared_chars, own_chars,"
            " own_tokens, own_in_margin, has_own_text, own_sentence_keys"
            " FROM {analysis}.text_family_member")):
        fam = families[fid]
        fam.members[cid] = Member(cid, via, cov, None, shared, own, own_tokens, margin,
                                  has_own, json.loads(own_keys) if own_keys is not None else None)
        if via == "core":
            fam.core.append(cid)
    for fam in families.values():
        fam.core.sort()
    return families, sizes


# ----------------------------------------------------------- the delta

class Increment:
    """One incremental delta over the stored families. compute() decides it in
    memory and prints what it found; write(cur) applies it."""

    def __init__(self, conn, ctx, first_seen, dedup_rows):
        self.conn, self.ctx = conn, ctx
        self.first_seen = first_seen
        # dedup_rows: {cid: (content_hash, middle_hash, original_comment_id,
        # is_original, duplicate_group_size)}
        self.dedup_rows = dedup_rows
        self.families = {}          # fid (stored, or negative temp) -> Family
        self.sizes = {}             # stored fid -> (n_texts, n_comments, is_campaign)
        self.weight = {}
        self.survivors = set()
        self.stats = defaultdict(int)
        # the write plan
        self.removed_members = []   # member ids whose text has a new original
        self.merges = []            # (into, from)
        self.absorbed = set()
        self.new_families = []      # Family with temp ids
        self.dropped_new = 0
        self.new_members = defaultdict(list)     # stored fid -> [Member] to insert
        self.reattributed = defaultdict(set)     # fid -> member ids to (re)write attribution
        self.changed_ngrams = defaultdict(set)   # stored fid -> ngram ids to upsert
        self.changed_keys = defaultdict(set)     # stored fid -> sentence keys to upsert
        self.full_upsert = set()                 # stored fids whose every count row is rewritten
        self.size_changed = set()
        self.joined_core = set()                 # texts that joined a stored family as core
        self.cf = {}
        self._next_temp = 0                      # temp ids for new families: -1, -2, ... never reused

    def _temp_id(self):
        """A new family's id until it is written: negative, and never handed
        out twice. Numbering from the count of families kept so far reused
        an id when a family failed the floor between two batches, and the
        second batch's family overwrote the first's."""
        self._next_temp -= 1
        return self._next_temp

    # ---- steps

    def compute(self):
        t0 = time.time()
        conn, ctx = self.conn, self.ctx
        stored_partition = {c for (c,) in conn.execute(ctx.render_sql(
            "SELECT comment_id FROM {analysis}.comment_group_member"))}
        new_ids = sorted(c for c in self.first_seen if c not in stored_partition)
        self.stats["new_comments"] = len(new_ids)
        self.families, self.sizes = load_stored(conn, ctx)
        _step(f"incremental: {len(new_ids):,} comment(s) not in the partition;"
              f" {len(self.families):,} stored families ({time.time() - t0:.0f}s)")

        weight, original_of, is_original, middle_class, middle_of = {}, {}, set(), defaultdict(list), {}
        for cid, (_ch, mh, orig, is_orig, size) in self.dedup_rows.items():
            original_of[cid] = cid if is_orig else (orig or cid)
            if is_orig:
                is_original.add(cid)
                weight[cid] = size or 1
            if mh:
                middle_class[mh].append(cid)
                middle_of[cid] = mh
        self.weight = weight
        fm.set_weights(weight)
        member_family = {}
        for fid, fam in self.families.items():
            for cid in fam.members:
                member_family[cid] = fid
        self.survivors = {c for (c,) in conn.execute(ctx.render_sql(
            "SELECT comment_id FROM {analysis}.substance_floor WHERE NOT floored"))}

        # ---- copies and displaced originals
        delta_w = defaultdict(int)
        new_texts = []
        for c in new_ids:
            if c not in self.dedup_rows:
                self.stats["no_dedup_row"] += 1
                continue
            if c in is_original:
                new_texts.append(c)
            else:
                delta_w[original_of[c]] += 1
        self.stats["copies"] = sum(delta_w.values())
        self.stats["new_texts"] = len(new_texts)
        # A stored member whose text now has a different original (a lower
        # id arrived): the member row moves to the new original, same
        # family, same way in; the text is the same bytes.
        rekeyed = {}
        for cid in list(member_family):
            if cid in is_original:
                continue
            fid = member_family.pop(cid)
            fam = self.families[fid]
            old = fam.members.pop(cid)
            if cid in fam.core:
                fam.core.remove(cid)
            self.removed_members.append(cid)
            new_orig = original_of.get(cid)
            if new_orig is None or new_orig not in weight or new_orig in member_family:
                continue
            m = Member(new_orig, old.joined_via, old.coverage)
            fam.members[new_orig] = m
            member_family[new_orig] = fid
            if old.joined_via == "core":
                fam.core.append(new_orig)
            self.new_members[fid].append(m)
            rekeyed[new_orig] = fid
            self.size_changed.add(fid)
            if new_orig in self.survivors:
                self.reattributed[fid].add(new_orig)
        self.stats["rekeyed"] = len(rekeyed)

        unfamilied = sorted(t for t in weight if t not in member_family)
        touch = set(new_texts) | set(delta_w)
        sets = fetch_sets(conn, ctx, set(unfamilied) | touch | set(rekeyed))
        _step(f"  {len(new_texts):,} new text(s), {self.stats['copies']:,} copies of"
              f" {len(delta_w):,} text(s); {len(unfamilied):,} texts in no family;"
              f" n-gram sets loaded ({time.time() - t0:.0f}s)")

        # ---- cores: detector groups and middle classes the arrivals touched
        touch_ids = sorted(touch | set(new_ids))
        near = defaultdict(set)
        for chunk in _chunks(touch_ids):
            for gid, cid in conn.execute(ctx.render_sql(
                    "SELECT m.group_id, m.comment_id FROM {analysis}.duplicate_group_members m"
                    " WHERE m.group_id IN (SELECT group_id FROM {analysis}.duplicate_group_members"
                    " WHERE comment_id IN (SELECT value FROM json_each(?)))"), (json.dumps(chunk),)):
                near[gid].add(original_of.get(cid, cid))
        units = [("near", sorted(t for t in texts if t in weight))
                 for texts in near.values() if len(texts) >= 2]
        body_of = {}
        touched_classes = {middle_of[t] for t in touch if t in middle_of}
        for mh in sorted(touched_classes):
            cids = middle_class[mh]
            if len(cids) < 2:
                continue
            # A middle class of two or more comments binds its texts as one
            # unit and joins the cores holding any of them (the build's
            # rule); whether it can be a core of its own is the family
            # floor's decision in _found.
            texts = sorted({original_of[c] for c in cids})
            for t in texts:
                body_of[t] = mh
            units.append(("middle", [t for t in texts if t in weight]))
        core_family_of = {t: fid for t, fid in member_family.items()
                          if self.families[fid].members[t].joined_via == "core"}
        joins, merges, new_cores = resolve_components(units, core_family_of, member_family)
        for into, frm in merges:
            self._merge(into, frm, member_family)
        self.stats["merges"] = len(merges)
        decided = set()
        for kind, texts in new_cores:
            decided.update(texts)
        for fid, texts in joins.items():
            decided.update(texts)
        # A small middle class whose siblings are attached members: the
        # free texts attach to the same family as a unit.
        attach_joins = defaultdict(list)
        for mh in sorted(touched_classes):
            texts = sorted({original_of[c] for c in middle_class[mh]})
            fams = {member_family[t] for t in texts if t in member_family}
            free = [t for t in texts
                    if t not in member_family and t not in decided and t in weight]
            if len(fams) == 1 and free and not any(t in core_family_of for t in texts):
                attach_joins[min(fams)].extend(free)
                decided.update(free)

        # ---- exact cores: an original of enough copies in no family
        for t in sorted(touch):
            if t in member_family or t in decided or t not in weight:
                continue
            if weight[t] >= FAMILY_MIN_COMMENTS:
                siblings = ([s for s, mh in body_of.items() if mh == body_of[t]]
                            if t in body_of else [t])
                core = sorted(s for s in siblings
                              if s not in member_family and s not in decided) or [t]
                new_cores.append(("exact", core))
                decided.update(core)

        # ---- core joins into stored families, the core floor applied per unit
        contributions = defaultdict(lambda: defaultdict(int))   # fid -> text -> added
        for t, dw in delta_w.items():
            fid = member_family.get(t)
            if fid is not None and self.families[fid].members[t].joined_via == "core":
                contributions[fid][t] += dw
        released = []
        for fid, texts in sorted(joins.items()):
            fam = self.families[fid]
            for unit in fm.units(texts, body_of):
                unit_sets = [sets[c] for c in unit if c in sets]
                cov = fm.unit_coverage(unit_sets, fam.ngrams) if unit_sets else 0.0
                if cov >= MEMBERSHIP_FLOOR:
                    for c in unit:
                        m = Member(c, "core", cov)
                        fam.members[c] = m
                        fam.core.append(c)
                        member_family[c] = fid
                        self.new_members[fid].append(m)
                        self.joined_core.add(c)
                        contributions[fid][c] += weight.get(c, 1)
                        if c in self.survivors:
                            self.reattributed[fid].add(c)
                    self.stats["joined_core"] += len(unit)
                else:
                    released.extend(unit)
        for fid, texts in sorted(attach_joins.items()):
            fam = self.families[fid]
            unit = [t for t in texts if t not in member_family]
            if not unit:
                continue
            unit_sets = [sets[c] for c in unit if c in sets]
            cov = fm.unit_coverage(unit_sets, fam.ngrams) if unit_sets else 0.0
            for c in unit:
                m = Member(c, "attach", cov)
                fam.members[c] = m
                member_family[c] = fid
                self.new_members[fid].append(m)
                if c in self.survivors:
                    self.reattributed[fid].add(c)
            self.stats["joined_attach"] += len(unit)

        # ---- new families from the new cores
        self._found(new_cores, sets, body_of, member_family, weight)

        # ---- attach: new and released texts to every family; old texts to the new ones
        self._attach(sorted((set(new_texts) | set(released)) - set(member_family)),
                     sorted(t for t in unfamilied if t not in touch and t not in member_family),
                     sets, body_of, member_family, only_new=False)

        # ---- second pass: containment against the old pending texts
        shared = {ng for (ng,) in conn.execute(ctx.render_sql(
            "SELECT ngram_id FROM {analysis}.long_ngram_stats WHERE comment_frequency >= ?"),
            (FAMILY_MIN_COMMENTS,))}

        def pending(ts):
            return [t for t in ts if t in sets
                    and sum(1 for ng in sets[t] if ng in shared) >= SECOND_PASS_MIN_SHARED]
        new_pending = pending(t for t in sorted(touch) if t not in member_family)
        old_pending = pending(t for t in unfamilied if t not in touch and t not in member_family)
        groups = contain_against([(t, sets[t], weight.get(t, 1)) for t in old_pending],
                                 [(t, sets[t], weight.get(t, 1)) for t in new_pending],
                                 CONTAIN_THRESHOLD)
        contain_cores = [("contain", sorted(members)) for _leader, members in groups]
        self.stats["second_pass_new"] = len(new_pending)
        self.stats["second_pass_old"] = len(old_pending)
        _step(f"  second pass: {len(new_pending):,} new text(s) with repeated material against"
              f" {len(old_pending):,} old; {len(contain_cores):,} contain core(s)"
              f" ({time.time() - t0:.0f}s)")
        before = len(self.new_families)
        self._found(contain_cores, sets, body_of, member_family, weight)
        if len(self.new_families) > before:
            self._attach(sorted(t for t in touch if t not in member_family), [],
                         sets, body_of, member_family, only_new=True,
                         new_from=before)

        # ---- touched stored families: counts raised, family text extended
        self._raise(contributions, sets, member_family, weight, delta_w)

        # ---- attribution: new survivor members and the members a change reached
        self._attribute()

        # ---- sizes
        for fid, fam in self.families.items():
            if fid < 0:
                continue
            if fid in self.absorbed:
                continue
            if family_sizes(fam, weight) != self.sizes[fid]:
                self.size_changed.add(fid)
        self.stats["touched"] = len(contributions)
        self.stats["new_families"] = len(self.new_families)
        self.stats["reattributed"] = sum(len(v) for v in self.reattributed.values())
        self.stats["new_member_rows"] = sum(len(v) for v in self.new_members.values())
        _step(f"  delta decided in {time.time() - t0:.0f}s: {self.stats['joined_core']:,} joined"
              f" as core, {self.stats['joined_attach']:,} attached, {len(self.new_families):,}"
              f" new families ({self.dropped_new:,} dropped unattributed),"
              f" {len(merges):,} merges, {len(contributions):,} families with raised counts,"
              f" {self.stats['reattributed']:,} members attributed")
        return self

    def current_families(self):
        return [f for fid, f in self.families.items() if fid not in self.absorbed]

    # ---- helpers

    def _merge(self, into, frm, member_family):
        a, b = self.families[into], self.families[frm]
        for cid, m in b.members.items():
            a.members[cid] = m
            member_family[cid] = into
        a.core = sorted(set(a.core) | set(b.core))
        merge_counts(a.ngrams, b.ngrams)
        merge_counts(a.sentence_counts, b.sentence_counts)
        a.sentence_keys = fm.keys_at_threshold(a.sentence_counts, a.family_text_min)
        self.full_upsert.add(into)
        self.absorbed.add(frm)
        self.merges.append((into, frm))
        self.size_changed.add(into)
        for cid in a.members:
            if cid in self.survivors:
                self.reattributed[into].add(cid)
        b.members = {}
        b.core = []

    def _found(self, cores, sets, body_of, member_family, weight):
        """New families from these cores: family text, distinctive, the
        core floor, the exemplar, the family floor, the sentence counts."""
        if not cores:
            return
        fams = []
        for kind, texts in cores:
            texts = [t for t in texts if t not in member_family]
            if not texts:
                continue
            fam = Family(family_id=self._temp_id(), core_kind=kind, core=sorted(texts))
            fam.ngrams, fam.family_text_min = fm.family_text(fam.core, sets, weight)
            fams.append(fam)
        if not fams:
            return
        fetch_frequency(self.conn, self.ctx, {ng for f in fams for ng in f.ngrams}, self.cf)
        for fam in fams:
            fam.distinctive = fm.distinctive_ngrams(fam.core, fam.ngrams, sets, weight, self.cf)
        assigned = {}
        fm._core_floor(fams, sets, body_of, assigned)
        kept = []
        for fam in fams:
            if fam.members and fam.n_comments(weight) >= FAMILY_MIN_COMMENTS:
                kept.append(fam)
            else:
                self.stats["new_family_under_floor"] += 1
        texts = fetch_texts(self.conn, self.ctx, {c for f in kept for c in f.core})
        for fam in kept:
            fam.core = sorted(fam.members)
            fam.sentence_counts = fm.family_sentence_counts(fam.core, texts, weight)
            fam.sentence_keys = fm.keys_at_threshold(fam.sentence_counts, fam.family_text_min)
            for cid in fam.members:
                member_family[cid] = fam.family_id
                if cid in self.survivors:
                    self.reattributed[fam.family_id].add(cid)
            self.families[fam.family_id] = fam
            self.new_families.append(fam)

    def _attach(self, new_texts, old_texts, sets, body_of, member_family, only_new,
                new_from=0):
        """new_texts are offered to every family (or, with only_new, to the
        new families from index new_from on); old_texts to the new families."""
        new_fams = self.new_families[new_from:]
        index_new, index_all = {}, {}
        for fam in new_fams:
            for ng in fam.distinctive:
                index_new[ng] = fam.family_id
        if not only_new:
            for fam in self.current_families():
                for ng in fam.distinctive:
                    index_all[ng] = fam.family_id
        by_id = {f.family_id: f for f in self.current_families()}
        plans = []
        if new_texts:
            plans.append((new_texts, index_new if only_new else index_all))
        if old_texts and index_new:
            plans.append((old_texts, index_new))
        for texts, index in plans:
            for fam, unit, cov in attach_units(fm.units(texts, body_of), index, by_id, sets):
                for c in unit:
                    if c in member_family:
                        continue
                    m = Member(c, "attach", cov)
                    fam.members[c] = m
                    member_family[c] = fam.family_id
                    if fam.family_id >= 0:
                        self.new_members[fam.family_id].append(m)
                    if c in self.survivors:
                        self.reattributed[fam.family_id].add(c)
                    self.stats["joined_attach"] += 1

    def _raise(self, contributions, sets, member_family, weight, delta_w):
        """Raise the touched families' counts. An n-gram not in a family's
        text has no stored count; the ones that could cross the threshold
        (corpus frequency at the threshold or more) are measured over the
        family's stored core with the weights those texts had before this
        run, then the contributions are added."""
        conn, ctx = self.conn, self.ctx
        # Redirect contributions to absorbed families.
        for frm in list(contributions):
            if frm in self.absorbed:
                into = next(i for i, f in self.merges if f == frm)
                for t, dw in contributions.pop(frm).items():
                    contributions[into][t] += dw
        candidates = {}     # fid -> {ngram: added}
        for fid, contribs in contributions.items():
            fam = self.families[fid]
            changed, cand = raised_counts(fam.ngrams, contribs, sets, fam.family_text_min)
            self.changed_ngrams[fid].update(changed)
            candidates[fid] = cand
        fetch_frequency(conn, ctx, {ng for c in candidates.values() for ng in c}, self.cf)
        measure = defaultdict(set)   # ngram -> fids that need its inside count
        for fid, cand in candidates.items():
            n_min = self.families[fid].family_text_min
            for ng in cand:
                if (self.cf.get(ng) or 0) >= n_min:
                    measure[ng].add(fid)
        inside = defaultdict(int)    # (fid, ngram) -> the count before this run
        for chunk in _chunks(measure):
            for ng, cid in conn.execute(ctx.render_sql(
                    "SELECT DISTINCT ngram_id, comment_id FROM {analysis}.comment_long_ngrams"
                    " WHERE ngram_id IN (SELECT value FROM json_each(?))"), (json.dumps(chunk),)):
                fid = member_family.get(cid)
                if fid is None or fid not in measure[ng] or cid in self.joined_core:
                    continue      # a text that joined this run is wholly in the contribution
                m = self.families[fid].members.get(cid)
                if m is None or m.joined_via != "core":
                    continue
                inside[(fid, ng)] += weight.get(cid, 1) - delta_w.get(cid, 0)
        added_ngrams = defaultdict(set)
        for fid, cand in candidates.items():
            fam = self.families[fid]
            for ng, dw in cand.items():
                total = inside.get((fid, ng), 0) + dw
                if fid in measure.get(ng, ()) and total >= fam.family_text_min:
                    fam.ngrams[ng] = total
                    added_ngrams[fid].add(ng)
                    self.changed_ngrams[fid].add(ng)
        # Sentences.
        texts = fetch_texts(conn, ctx, {t for c in contributions.values() for t in c})
        keys_of = {t: fm.text_sentence_keys(text) for t, text in texts.items()}
        added_keys = {}
        for fid, contribs in contributions.items():
            fam = self.families[fid]
            changed, added = raised_sentences(fam.sentence_counts, contribs, keys_of,
                                              fam.family_text_min)
            self.changed_keys[fid].update(changed)
            fam.sentence_keys = fm.keys_at_threshold(fam.sentence_counts, fam.family_text_min)
            added_keys[fid] = added
        # Distinctive, over the whole family text of every touched family.
        touched = set(contributions) | (self.full_upsert & set(self.families))
        fetch_frequency(conn, ctx, {ng for fid in touched for ng in self.families[fid].ngrams},
                        self.cf)
        for fid in touched:
            fam = self.families[fid]
            before = set(fam.distinctive)
            fam.distinctive = set()
            for ng, n in fam.ngrams.items():
                total = self.cf.get(ng)
                if not total:
                    raise SystemExit(
                        f"long_ngram_stats has no comment_frequency for n-gram {ng} — run"
                        " comments_db/scripts/extract_long_ngrams.py --update-stats first.")
                if n / total >= DISTINCTIVE_SHARE:
                    fam.distinctive.add(ng)
            self.changed_ngrams[fid].update(before ^ fam.distinctive)
        # The members a change reached.
        by_ngram = defaultdict(set)
        for fid, ngs in added_ngrams.items():
            for ng in ngs:
                by_ngram[ng].add(fid)
        for chunk in _chunks(by_ngram):
            for ng, cid in conn.execute(ctx.render_sql(
                    "SELECT DISTINCT ngram_id, comment_id FROM {analysis}.comment_long_ngrams"
                    " WHERE ngram_id IN (SELECT value FROM json_each(?))"), (json.dumps(chunk),)):
                fid = member_family.get(cid)
                if fid in by_ngram[ng] and cid in self.survivors:
                    self.reattributed[fid].add(cid)
        for fid, keys in added_keys.items():
            if not keys:
                continue
            for (cid,) in conn.execute(ctx.render_sql(
                    "SELECT comment_id FROM {analysis}.text_family_member"
                    " WHERE family_id = ? AND EXISTS (SELECT 1 FROM json_each(own_sentence_keys) k"
                    "   WHERE k.value IN (SELECT value FROM json_each(?)))"), (fid, json.dumps(sorted(keys)))):
                if cid in self.families[fid].members and cid in self.survivors:
                    self.reattributed[fid].add(cid)
        self.stats["added_ngrams"] = sum(len(v) for v in added_ngrams.values())
        self.stats["added_keys"] = sum(len(v) for v in added_keys.values())

    def _attribute(self):
        ids = sorted({c for s in self.reattributed.values() for c in s})
        if not ids:
            return
        t0 = time.time()
        texts = fetch_texts(self.conn, self.ctx, ids)
        occ = fetch_occurrences(self.conn, self.ctx, ids)
        for fid, cids in self.reattributed.items():
            fam = self.families[fid]
            for cid in cids:
                fm.attribute_member(fam.members[cid], texts.get(cid, ""), fam, occ.get(cid, []))
        # A new family whose surviving members carry none of its text has no
        # letter to score (families.drop_unattributed).
        kept = []
        for fam in self.new_families:
            attributed = [m for m in fam.members.values() if m.spans is not None]
            if attributed and not any((m.shared_chars or 0) > 0 for m in attributed):
                self.dropped_new += 1
                del self.families[fam.family_id]
                self.reattributed.pop(fam.family_id, None)
                continue
            kept.append(fam)
        self.new_families = kept
        _step(f"  attribution: {len(ids):,} member(s) ({time.time() - t0:.0f}s)")

    # ---- write

    def write(self, cur):
        """Apply the delta inside the caller's transaction. Returns
        {family id as the partition names it: stored family id}: identity
        for stored families, temp -> real for the new ones."""
        ctx = self.ctx
        weight = self.weight
        if self.removed_members:
            cur.execute(ctx.render_sql(
                "DELETE FROM {analysis}.text_family_member WHERE comment_id IN (SELECT value FROM json_each(?))"),
                (json.dumps(self.removed_members),))
        for into, frm in self.merges:
            cur.execute(ctx.render_sql(
                "UPDATE {analysis}.text_family_member SET family_id = ? WHERE family_id = ?"),
                (into, frm))
            cur.execute(ctx.render_sql(
                "DELETE FROM {analysis}.text_family WHERE family_id = ?"), (frm,))
        id_map = {fid: fid for fid in self.families if fid >= 0}
        for fam in self.new_families:
            n_texts, n_comments, is_campaign = family_sizes(fam, weight)
            row = cur.execute(ctx.render_sql(
                "INSERT INTO {analysis}.text_family (exemplar_comment_id, core_kind, n_texts,"
                " n_comments, is_campaign, family_text_min, params)"
                " VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING family_id"),
                (fam.exemplar_id, fam.core_kind, n_texts, n_comments, is_campaign,
                 fam.family_text_min, json.dumps(fm.PARAMS))).fetchone()
            assert row is not None
            id_map[fam.family_id] = row[0]
            fid = row[0]
            cur.executemany(ctx.render_sql(
                "INSERT INTO {analysis}.text_family_ngram (family_id, ngram_id, n_core_texts,"
                " distinctive) VALUES (?, ?, ?, ?)"),
                [(fid, ng, n, ng in fam.distinctive) for ng, n in fam.ngrams.items()])
            cur.executemany(ctx.render_sql(
                "INSERT INTO {analysis}.text_family_sentence (family_id, sentence_key,"
                " n_comments) VALUES (?, ?, ?)"),
                [(fid, k, n) for k, n in fam.sentence_counts.items()])
            self._insert_members(cur, fid, fam.members.values())
        for fid in sorted(self.changed_ngrams):
            fam = self.families[fid]
            ngs = fam.ngrams if fid in self.full_upsert else self.changed_ngrams[fid]
            cur.executemany(ctx.render_sql(
                "INSERT INTO {analysis}.text_family_ngram (family_id, ngram_id, n_core_texts,"
                " distinctive) VALUES (?, ?, ?, ?)"
                " ON CONFLICT (family_id, ngram_id) DO UPDATE"
                " SET n_core_texts = EXCLUDED.n_core_texts, distinctive = EXCLUDED.distinctive"),
                [(fid, ng, fam.ngrams[ng], ng in fam.distinctive) for ng in sorted(ngs)
                 if ng in fam.ngrams])
        for fid in sorted(set(self.changed_keys) | self.full_upsert):
            fam = self.families[fid]
            keys = fam.sentence_counts if fid in self.full_upsert else self.changed_keys[fid]
            cur.executemany(ctx.render_sql(
                "INSERT INTO {analysis}.text_family_sentence (family_id, sentence_key,"
                " n_comments) VALUES (?, ?, ?)"
                " ON CONFLICT (family_id, sentence_key) DO UPDATE"
                " SET n_comments = EXCLUDED.n_comments"),
                [(fid, k, fam.sentence_counts[k]) for k in sorted(keys)
                 if k in fam.sentence_counts])
        for fid in sorted(self.size_changed):
            if fid in self.absorbed:
                continue
            n_texts, n_comments, is_campaign = family_sizes(self.families[fid], weight)
            cur.execute(ctx.render_sql(
                "UPDATE {analysis}.text_family SET n_texts = ?, n_comments = ?,"
                " is_campaign = ?, built_at = CURRENT_TIMESTAMP WHERE family_id = ?"),
                (n_texts, n_comments, is_campaign, fid))
        for fid, members in sorted(self.new_members.items()):
            self._insert_members(cur, fid, members)
        inserted = {m.comment_id for ms in self.new_members.values() for m in ms}
        for fid, cids in sorted(self.reattributed.items()):
            if fid < 0:
                continue
            fam = self.families[fid]
            rows = [fam.members[c] for c in sorted(cids) if c not in inserted]
            if not rows:
                continue
            cur.executemany(ctx.render_sql(
                "UPDATE {analysis}.text_family_member SET shared_chars = ?, own_chars = ?,"
                " own_tokens = ?, own_in_margin = ?, has_own_text = ?,"
                " own_sentence_keys = ? WHERE comment_id = ?"),
                [(m.shared_chars, m.own_chars, m.own_tokens, m.own_in_margin, m.has_own_text,
                  json.dumps(m.own_keys) if m.own_keys is not None else None, m.comment_id) for m in rows])
            cur.execute(ctx.render_sql(
                "DELETE FROM {analysis}.text_family_span WHERE comment_id IN (SELECT value FROM json_each(?))"),
                (json.dumps([m.comment_id for m in rows]),))
            self._insert_spans(cur, rows)
        # Distinctive is a share of a corpus count that grows every hour:
        # refresh every family's flags against the current frequencies so
        # the next run's attach reads flags that are not an hour stale.
        cur.execute(ctx.render_sql(
            "UPDATE {analysis}.text_family_ngram AS n SET distinctive = x.d"
            " FROM (SELECT n2.family_id, n2.ngram_id,"
            "              (CAST(n2.n_core_texts AS REAL) / s.comment_frequency >= ?) AS d"
            "       FROM {analysis}.text_family_ngram n2"
            "       JOIN {analysis}.long_ngram_stats s USING (ngram_id)"
            "       WHERE s.comment_frequency > 0) x"
            " WHERE n.family_id = x.family_id AND n.ngram_id = x.ngram_id"
            " AND n.distinctive <> x.d"), (DISTINCTIVE_SHARE,))
        self.stats["distinctive_refreshed"] = cur.rowcount
        return id_map

    def _insert_members(self, cur, fid, members):
        members = list(members)
        cur.executemany(self.ctx.render_sql(
            "INSERT INTO {analysis}.text_family_member (comment_id, family_id, joined_via,"
            " coverage, shared_chars, own_chars, own_tokens, own_in_margin, has_own_text,"
            " own_sentence_keys) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"),
            [(m.comment_id, fid, m.joined_via, m.coverage, m.shared_chars, m.own_chars,
              m.own_tokens, m.own_in_margin, m.has_own_text,
              json.dumps(m.own_keys) if m.own_keys is not None else None) for m in members])
        self._insert_spans(cur, members)

    def _insert_spans(self, cur, members):
        rows = [(m.comment_id, a, b, tier) for m in members for a, b, tier in (m.spans or ())]
        if rows:
            cur.executemany(self.ctx.render_sql(
                "INSERT INTO {analysis}.text_family_span (comment_id, char_start, char_end,"
                " tier) VALUES (?, ?, ?, ?)"), rows)

    def report(self):
        s = self.stats
        print(f"\nincremental delta: {s['new_comments']:,} new comment(s):"
              f" {s['copies']:,} copies, {s['new_texts']:,} new texts,"
              f" {s['no_dedup_row']:,} with no dedup row, {s['rekeyed']:,} member text(s)"
              " re-keyed to a new original")
        print(f"  joined stored families: {s['joined_core']:,} as core,"
              f" {s['joined_attach']:,} attached")
        print(f"  new families: {len(self.new_families):,}"
              f" ({s['new_family_under_floor']:,} under the floor, {self.dropped_new:,} with"
              " nothing attributed, both discarded)")
        for fam in sorted(self.new_families, key=lambda f: -f.n_comments(self.weight)):
            print(f"    {fam.core_kind:<7} exemplar {fam.exemplar_id}  texts {fam.n_texts:,}"
                  f"  comments {fam.n_comments(self.weight):,}")
        print(f"  merges: {len(self.merges):,}"
              + "".join(f"\n    family {frm} into family {into}" for into, frm in self.merges))
        print(f"  families with raised counts: {s['touched']:,};"
              f" {s['added_ngrams']:,} n-gram(s) and {s['added_keys']:,} sentence(s) joined a"
              f" family text; {s['reattributed']:,} member(s) attributed;"
              f" {len(self.size_changed):,} family size(s) changed")
