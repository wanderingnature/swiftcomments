#!/usr/bin/env python3
"""Text families: which comments are copies of one letter, and which part of
each copy the signer wrote.

The governing rule (docs/design/shared-text-families.md, section 1):
membership first, attribution second. A member's shared text is its
family's; a non-member's text is all its own; no passage gets a global label;
a passage used by several campaigns never decides membership. Document
frequency is evidence for finding families, not the definition of shared
text.

Built here, in memory, from four things the pipeline already has: the exact
and middle hash classes (comment_dedup), the n-gram sets with offsets
(comment_long_ngrams, one original per exact class), the near-duplicate
detector's groups (duplicate_group_members, leader assignment), and the
floor survivors' texts. Written by build_comment_groups.py --write, in one
transaction with the partition, and read back by shared_text.load_shapes.
docs/design/shared-text-families-implementation.md, section 5, is the spec;
the constants are in shared_text.

    uv run python scripts/substance/families.py --project roadless

is the dry run: stage counts, the review list, the largest families and the
R7 check, nothing written.

Stages, in order (each prints its counts):

  cores        near (detector groups), middle (middle classes of 3+ comments
               with no text in a near core), exact (originals of 3+ copies
               in no other core). A text is in at most one core. A middle
               class whose texts sit in two or more near cores JOINS those
               cores into one family: a middle class is byte identity of
               the body, and the detector's size buckets separate copies
               whose tails differ in length (244 classes on roadless), so
               the identical body is the stronger evidence. Every such join
               is reported. This is not the hash-hopping that over-merged
               the partition once (docs/design/comment-groups-and-claim-
               keys.md): the relation joining two cores here is one
               identical body, never a chain through a third layer.
  exemplar     the most-copied core text; when none repeats, the highest
               mean Jaccard to a sample of core texts; comment_id breaks ties.
  family text  n-grams that FAMILY_MIN_COMMENTS comments of the core share,
               copies counted: a pinned number, not a share of the core.
  distinctive  family text whose comment-weighted corpus occurrences fall
               DISTINCTIVE_SHARE inside this family. Rule 5, mechanically.
  core floor   a core text under MEMBERSHIP_FLOOR against the family text
               leaves the core and goes to attach with everything else.
  attach       a text outside every core joins the family whose distinctive
               text covers the largest share of its n-grams, at or above
               MEMBERSHIP_FLOOR. To the family text, never to a member.
  family floor n_comments (copies counted) under FAMILY_MIN_COMMENTS
               dissolves the family; its texts go back to attach.
               is_campaign at CAMPAIGN_MIN_COMMENTS.
  second pass  the texts still in no family that carry any repeated
               material (SECOND_PASS_MIN_SHARED n-grams shared by
               FAMILY_MIN_COMMENTS+ comments) are grouped by CONTAINMENT
               without size buckets (shared/near_duplicates.py, threshold
               CONTAIN_THRESHOLD, shortest text leads): a letter carried
               inside longer personal comments is contained in each of them,
               which the first pass cannot see because no two copies are
               near-identical or the same length. Groups become `contain`
               cores and go through family text, distinctive, the core
               floor, attach and the family floor like the others. On
               roadless the first pass alone left 87 such letters, one of
               5,708 copies, scored once per signer.
  attribution  survivors only, sentence by sentence: tier 1 the sentence key
               is one enough core texts share (the family-text threshold,
               copies counted; a sentence one core text wrote is that
               signer's); tier 2 the family's n-gram occurrences cover
               SENTENCE_COVERAGE of it; else the signer's. Then the
               trivial-own rule, and the MIN_OWN_CHARS floor (own text under 50
               characters, anywhere, is not own text).
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[2]))
sys.path.insert(0, str(_HERE.parent))

from shared import db, text_norm  # noqa: E402
from shared.near_duplicates import assign_leaders  # noqa: E402
from shared.project_context import add_project_argument, context_from_args  # noqa: E402
import shared_text  # noqa: E402
from shared_text import (  # noqa: E402
    CAMPAIGN_MIN_COMMENTS, CONTAIN_THRESHOLD, DISTINCTIVE_SHARE, EXEMPLAR_SAMPLE,
    FAMILY_MIN_COMMENTS, MEMBERSHIP_FLOOR, MIN_OWN_CHARS, SECOND_PASS_MIN_SHARED,
    SENTENCE_COVERAGE, TRIVIAL_OWN_TOKENS)

PARAMS = {
    "FAMILY_MIN_COMMENTS": FAMILY_MIN_COMMENTS,
    "CAMPAIGN_MIN_COMMENTS": CAMPAIGN_MIN_COMMENTS,
    "MEMBERSHIP_FLOOR": MEMBERSHIP_FLOOR,
    "DISTINCTIVE_SHARE": DISTINCTIVE_SHARE,
    "SENTENCE_COVERAGE": SENTENCE_COVERAGE,
    "TRIVIAL_OWN_TOKENS": TRIVIAL_OWN_TOKENS,
    "MIN_OWN_CHARS": MIN_OWN_CHARS,
    "EXEMPLAR_SAMPLE": EXEMPLAR_SAMPLE,
    "CONTAIN_THRESHOLD": CONTAIN_THRESHOLD,
    "SECOND_PASS_MIN_SHARED": SECOND_PASS_MIN_SHARED,
}

_CHUNK = 20000


def _step(msg):
    print(msg, flush=True)


@dataclass
class Member:
    comment_id: str
    joined_via: str                       # core | attach
    coverage: float
    spans: list | None = None             # [(start, end, tier)] for a survivor
    shared_chars: int | None = None
    own_chars: int | None = None
    own_tokens: int | None = None
    own_in_margin: bool | None = None
    has_own_text: bool = False
    own_keys: list | None = None          # norm keys of the own sentences, survivors only


@dataclass
class Family:
    family_id: int                        # 1-based within a full build; the stored id after
    core_kind: str                        # exact | middle | near | contain
    core: list                            # comment ids of the core texts
    leaders: list = field(default_factory=list)      # detector leaders of the near cores joined
    members: dict = field(default_factory=dict)      # comment_id -> Member
    exemplar_id: str = ""
    ngrams: dict = field(default_factory=dict)       # ngram_id -> comment-weighted core count
    distinctive: set = field(default_factory=set)
    family_text_min: int = 0
    sentence_keys: set = field(default_factory=set)
    sentence_counts: dict = field(default_factory=dict)  # norm key -> weighted core count, all keys

    @property
    def n_texts(self):
        return len(self.members)

    def n_comments(self, weight):
        return sum(weight.get(c, 1) for c in self.members)


# ------------------------------------------------------------- pure parts

def family_text(core, ngrams, weight):
    """{ngram_id: comments} over the core: the n-grams that at least
    FAMILY_MIN_COMMENTS comments of the core contain, each core text counting
    its copies. A pinned count, not a share of the core: the owner's rule
    (2026-09-20) is that thresholds name a number of comments, because a
    share moves with corpus size, and the three that make a family are the
    three that make a passage the family's. A one-text exact core of three
    or more copies has its whole text as family text."""
    count = defaultdict(int)
    for c in core:
        w = weight.get(c, 1)
        for ng in ngrams.get(c, ()):
            count[ng] += w
    return ({ng: n for ng, n in count.items() if n >= FAMILY_MIN_COMMENTS},
            FAMILY_MIN_COMMENTS)


def distinctive_ngrams(core, fam_ngrams, ngrams, weight, comment_frequency):
    """The family-text n-grams whose comment-weighted corpus occurrences fall
    at least DISTINCTIVE_SHARE inside this family's core."""
    occ = defaultdict(int)
    for c in core:
        w = weight.get(c, 1)
        for ng in ngrams.get(c, ()):
            if ng in fam_ngrams:
                occ[ng] += w
    out = set()
    for ng, inside in occ.items():
        total = comment_frequency.get(ng)
        if not total:
            raise SystemExit(
                f"long_ngram_stats has no comment_frequency for n-gram {ng} — run"
                " comments_db/scripts/extract_long_ngrams.py --update-stats first.")
        if inside / total >= DISTINCTIVE_SHARE:
            out.add(ng)
    return out


def text_sentence_keys(text):
    """The distinct normalized sentence keys of one text, blank ones dropped."""
    keys = set()
    for _a, _b, s in text_norm.sentences(text or ""):
        k = shared_text.norm_sentence(s)
        if k:
            keys.add(k)
    return keys


def family_sentence_counts(core, texts, weight):
    """{norm key: comments} over the core, every key including the ones
    under the threshold: each core text counts its copies once per distinct
    sentence. Stored whole (text_family_sentence) so the hourly step can
    raise a count when a core text or a copy arrives and never re-split the
    core."""
    count = defaultdict(int)
    for c in core:
        w = weight.get(c, 1)
        for k in text_sentence_keys(texts.get(c, "")):
            count[k] += w
    return dict(count)


def family_sentence_keys(core, texts, weight, n_min):
    """The family's sentences: the normalized keys that at least n_min
    comments of the core share (FAMILY_MIN_COMMENTS), each core text
    counting its copies. The same rule as the family text, and for the same
    reason: a sentence only one core text contains is that signer's own
    ("I have been a firefighter for 20 years in the Northeast US"), and a
    set built from every core text would hand it to the campaign for the
    very member who wrote it. A one-text exact core of three or more copies
    has all of its sentences as the letter's."""
    return keys_at_threshold(family_sentence_counts(core, texts, weight), n_min)


def keys_at_threshold(counts, n_min):
    return {k for k, n in counts.items() if n >= n_min}


def own_sentence_keys(text, spans):
    """The norm keys of the sentences attribute() left to the signer: every
    sentence whose span is not one of the campaign's. Stored on the member
    row so the hourly step can find, by array overlap, the members whose own
    sentence a later core text or copy turned into the family's."""
    shared = {(a, b) for a, b, _tier in (spans or ())}
    keys = set()
    for a, b, s in text_norm.sentences(text or ""):
        if (a, b) in shared:
            continue
        k = shared_text.norm_sentence(s)
        if k:
            keys.add(k)
    return sorted(keys)


def coverage(text_ngrams, fam_ngrams):
    """Share of a text's n-grams that are in the family text."""
    if not text_ngrams:
        return 0.0
    return sum(1 for ng in text_ngrams if ng in fam_ngrams) / len(text_ngrams)


def unit_coverage(sets, fam_ngrams):
    """Coverage of a unit of body-identical texts: their hits over their
    n-gram counts, summed. NOT the coverage of the union of their sets: a
    7,823-copy class's union is dominated by each copy's own name n-grams,
    and the union's coverage fell under the floor for every copy at once
    (45,943 core texts left their family on the first run)."""
    hits = total = 0
    for s in sets:
        total += len(s)
        hits += sum(1 for ng in s if ng in fam_ngrams)
    return hits / total if total else 0.0


def choose_exemplar(core, ngrams, weight):
    """The most-copied core text. When the largest weight is tied, the tied
    text with the highest mean Jaccard to a sample of the core; comment_id
    breaks what remains."""
    top = max(weight.get(c, 1) for c in core)
    candidates = sorted(c for c in core if weight.get(c, 1) == top)
    if len(candidates) == 1:
        return candidates[0]
    sample = sorted(core)[:EXEMPLAR_SAMPLE]

    def mean_jaccard(c):
        a = ngrams.get(c, frozenset())
        if not a:
            return 0.0
        total = 0.0
        for s in sample:
            b = ngrams.get(s, frozenset())
            union = len(a | b)
            total += len(a & b) / union if union else 0.0
        return total / len(sample)
    return min(candidates, key=lambda c: (-mean_jaccard(c), c))


def attribute(text, family_keys, fam_ngrams, occurrences):
    """One survivor member's split. occurrences: [(ngram_id, start, end)] of
    the member's own n-grams. Returns (spans, shared_chars, own_chars,
    own_tokens, own_in_margin, has_own_text)."""
    spans = []
    own_spans = []
    shared_chars = own_chars = 0
    covered = _union(sorted((a, b) for ng, a, b in occurrences if ng in fam_ngrams))
    tokens = text_norm.tokenize(text)
    # Tier 2 is measured over the sentence's TOKENS: a token is covered when
    # its span lies inside a covered interval. Measured over characters, the
    # form's '<br/><br/>' at the head of a sentence sat in the denominator and
    # pushed 'Besides, more roads mean more wildfire risk' under the rule.
    for a, b, s in text_norm.sentences(text):
        key = shared_text.norm_sentence(s)
        if key and key in family_keys:
            spans.append((a, b, 1))
            shared_chars += len(s)
            continue
        idx = [t for t in tokens if a <= t.start < b]
        hit = sum(1 for t in idx if _inside(covered, t.start, t.end))
        if idx and hit / len(idx) >= SENTENCE_COVERAGE:
            spans.append((a, b, 2))
            shared_chars += len(s)
            continue
        own_chars += len(s)
        lead = len(s) - len(s.lstrip())
        trail = len(s) - len(s.rstrip())
        if b - trail > a + lead:
            own_spans.append((a + lead, b - trail))
    own_tokens = sum(1 for t in tokens if any(a <= t.start < b for a, b in own_spans))
    # The margin is the first line and the last line. An own span is in it
    # when it starts in the first line or ends in the last: a closing
    # ('Thank you,<br/>Jane Smith') is one sentence to the splitter, which
    # does not cut on tags, but two lines to lines(), which does, so "lies
    # entirely within one line" missed exactly the signature the rule is for
    # (the leak test's six leaked closings, docs/reviews/shared-text-shadow-
    # run.md).
    lines = text_norm.lines(text)
    if lines:
        first, last = lines[0], lines[-1]
        own_in_margin = bool(own_spans) and all(
            (first[0] <= a < first[1]) or (last[0] < b <= last[1]) for a, b in own_spans)
    else:
        own_in_margin = False
    if own_tokens == 0:
        # Markup, punctuation, a stray bullet: nothing a model could score.
        has_own = False
    elif own_in_margin and own_tokens < TRIVIAL_OWN_TOKENS:
        has_own = False
    elif sum(b - a for a, b in own_spans) < MIN_OWN_CHARS:
        # Under 50 characters of own text, wherever it sits, carries no
        # substance worth a scoring call: the member is the campaign's text.
        has_own = False
    else:
        has_own = True
    return spans, shared_chars, own_chars, own_tokens, own_in_margin, has_own


def _union(ranges):
    out = []
    for a, b in ranges:
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _covered(union, a, b):
    total = 0
    for x, y in union:
        if y <= a:
            continue
        if x >= b:
            break
        total += min(y, b) - max(x, a)
    return total


def _inside(union, a, b):
    """Is [a, b) within one covered interval?"""
    for x, y in union:
        if x <= a and b <= y:
            return True
        if x >= b:
            return False
    return False


def cores(near, leader_of, middle_class, original_of, weight):
    """(families, review, assigned, body_of): the cores, each text in at most
    one, and body-identical texts always together.

    near: detector group id -> [text ids]; leader_of: group id -> leader;
    middle_class: middle hash -> [comment ids]; original_of: comment id ->
    its text (original) id; weight: text id -> exact-class size.

    Near cores first. Then each middle class of two or more comments (its
    texts share a body byte for byte): with a text in a near core it joins
    every near core holding one of its texts into one family and adds its
    remaining texts to that core; with none, and FAMILY_MIN_COMMENTS or more
    comments, it is a middle core; with none and fewer, its texts stay
    unassigned but bound (body_of), so attach and the core floor move them
    as one. review lists each class that joined two or more cores, with the
    leaders of the cores it joined. Then every original of
    FAMILY_MIN_COMMENTS or more copies still in no core is an exact core,
    together with its bound siblings."""
    near_cores = []                      # [(leader, [texts])]
    home = {}                            # text -> index into near_cores
    shared = []                          # (i, j): two detector groups holding one text
    for gid, texts in near.items():
        texts = sorted(set(texts))
        if len(texts) < 2:
            continue
        for t in texts:
            if t in home:
                shared.append((home[t], len(near_cores)))
            home[t] = len(near_cores)
        near_cores.append((leader_of.get(gid), texts))

    parent = list(range(len(near_cores)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    # A text in two detector groups makes them one core: the same text
    # cannot be two letters. The incremental detector put 949 comments into
    # a second group on 2026-09-21 and the partition failed on the overlap.
    for i, j in shared:
        parent[find(j)] = find(i)

    joined = defaultdict(set)            # near-core index -> texts joining through a middle class
    middle_cores, review = [], []
    body_of = {}                         # text -> middle hash, classes of 2+ comments
    for mh, cids in middle_class.items():
        if len(cids) < 2:
            continue
        texts = sorted({original_of.get(c, c) for c in cids})
        for t in texts:
            body_of[t] = mh
        homes = sorted({home[t] for t in texts if t in home})
        if not homes:
            if len(cids) >= FAMILY_MIN_COMMENTS:
                middle_cores.append(texts)
            continue
        root = find(homes[0])
        for h in homes[1:]:
            parent[find(h)] = root
        if len(homes) > 1:
            review.append((mh, len(cids), [near_cores[h][0] for h in homes]))
        joined[root].update(t for t in texts if t not in home)

    merged = defaultdict(lambda: ([], []))          # root -> (leaders, texts)
    for i, (leader, texts) in enumerate(near_cores):
        leaders, core = merged[find(i)]
        leaders.append(leader)
        core.extend(texts)
    for root, texts in joined.items():
        merged[find(root)][1].extend(texts)

    families, assigned = [], {}

    def new_family(kind, core, leaders=()):
        fam = Family(family_id=len(families) + 1, core_kind=kind, core=sorted(set(core)),
                     leaders=[l for l in leaders if l is not None])
        families.append(fam)
        for c in fam.core:
            assigned[c] = fam
        return fam

    for root in sorted(merged, key=lambda r: min(merged[r][1])):
        leaders, core = merged[root]
        new_family("near", core, leaders)
    n_near = len(families)
    n_joined = sum(1 for f in families if len(f.leaders) > 1)
    for texts in middle_cores:
        new_family("middle", texts)
    n_middle = len(families) - n_near
    siblings = defaultdict(list)
    for t, mh in body_of.items():
        siblings[mh].append(t)
    for text_id, w in sorted(weight.items()):
        if w >= FAMILY_MIN_COMMENTS and text_id not in assigned:
            bound = siblings.get(body_of.get(text_id), [text_id])
            new_family("exact", [t for t in bound if t not in assigned] or [text_id])
    n_exact = len(families) - n_near - n_middle
    _step(f"  cores: {n_near:,} near ({n_joined:,} joined through {len(review):,} middle"
          f" classes, {len(shared):,} detector groups merged for sharing a text),"
          f" {n_middle:,} middle, {n_exact:,} exact")
    return families, review, assigned, body_of


def units(texts, body_of):
    """Body-identical texts as one unit each; every other text alone."""
    by_body, out = defaultdict(list), []
    for t in texts:
        mh = body_of.get(t)
        if mh is None:
            out.append([t])
        else:
            by_body[mh].append(t)
    out.extend(by_body.values())
    return out


# ------------------------------------------------------------------ build

def build(conn, ctx):
    """(families, review, weight, survivors) — every family with its members
    and, for survivors, their attribution; review lists the middle classes
    whose texts sit in two or more near cores; weight is each original's
    exact-class size; survivors maps every floor survivor to its text."""
    t0 = time.time()
    _step("families: loading dedup, n-grams, detector groups, survivors...")
    weight, original_of, middle_class = {}, {}, defaultdict(list)
    for cid, mh, is_orig, orig, size in conn.execute(ctx.render_sql(
            "SELECT comment_id, middle_content_hash, is_original,"
            " original_comment_id, duplicate_group_size FROM {analysis}.comment_dedup")):
        original_of[cid] = cid if is_orig else orig
        if is_orig:
            weight[cid] = size or 1
        if mh:
            middle_class[mh].append(cid)
    ngrams = {}
    for cid, ids in conn.execute(ctx.render_sql(
            "SELECT comment_id, json_group_array(ngram_id) FROM {analysis}.comment_long_ngrams"
            " GROUP BY comment_id")):
        ngrams[cid] = frozenset(json.loads(ids))
    near = defaultdict(list)
    leader_of = {}
    for gid, cid, is_rep in conn.execute(ctx.render_sql(
            "SELECT group_id, comment_id, is_representative"
            " FROM {analysis}.duplicate_group_members")):
        text_id = original_of.get(cid, cid)
        near[gid].append(text_id)
        if is_rep:
            leader_of[gid] = text_id
    survivors = {cid: text or "" for cid, text in shared_text.load_corpus(conn, ctx.render_sql)}
    _step(f"  {len(weight):,} texts standing for {sum(weight.values()):,} comments;"
          f" {len(ngrams):,} n-gram sets; {len(near):,} detector groups;"
          f" {len(survivors):,} survivors ({time.time() - t0:.0f}s)")

    # ---- cores
    set_weights(weight)
    families, review, assigned, body_of = cores(near, leader_of, middle_class, original_of,
                                                weight)

    comment_frequency = {}
    _family_text(conn, ctx, families, ngrams, weight, comment_frequency, t0)
    _core_floor(families, ngrams, body_of, assigned)
    _attach(families, ngrams, body_of, assigned)
    families = _family_floor(families, assigned, weight, t0)

    # ---- second pass: containment over what is still in no family
    shared_ngrams = {row[0] for row in conn.execute(ctx.render_sql(
        "SELECT ngram_id FROM {analysis}.long_ngram_stats"
        " WHERE comment_frequency >= ?"), (FAMILY_MIN_COMMENTS,))}
    pending = [t for t, s in ngrams.items() if t not in assigned
               and sum(1 for ng in s if ng in shared_ngrams) >= SECOND_PASS_MIN_SHARED]
    _step(f"  second pass: {len(pending):,} text(s) in no family carry repeated material"
          f" ({len(shared_ngrams):,} n-grams in {FAMILY_MIN_COMMENTS}+ comments)")
    contained = contain_cores(pending, ngrams, weight, start_id=len(families) + 1)
    for fam in contained:
        for c in fam.core:
            assigned[c] = fam
    _step(f"  second pass: {len(contained):,} contain core(s) over"
          f" {sum(len(f.core) for f in contained):,} texts ({time.time() - t0:.0f}s)")
    _family_text(conn, ctx, contained, ngrams, weight, comment_frequency, t0)
    _core_floor(contained, ngrams, body_of, assigned)
    families = families + contained
    _attach(families, ngrams, body_of, assigned)
    families = _family_floor(families, assigned, weight, t0)
    # Texts a dissolved family released are offered to the survivors once more.
    _attach(families, ngrams, body_of, assigned)

    # ---- attribution, survivors only
    _attribute_all(conn, ctx, families, survivors, weight)
    families, dropped = drop_unattributed(families)
    _step(f"  {dropped:,} family(ies) dissolved: no surviving member carries any of their text")
    _step(f"families built in {time.time() - t0:.0f}s")
    return families, review, weight, survivors


def drop_unattributed(families):
    """(families, dropped): a family with surviving members none of whom
    carries a single campaign-attributed sentence has no letter to score.
    Its exemplar item would be blank, the queue would skip it, and the
    assembler would write no member rows at all. Eight attachment cover
    notes, each one sentence with a unique file id in the middle, were the
    case on roadless. Families with no surviving member are kept: nothing
    is scored for them either way, and their comment counts stand."""
    kept, dropped = [], 0
    for fam in families:
        attributed = [m for m in fam.members.values() if m.spans is not None]
        if attributed and not any((m.shared_chars or 0) > 0 for m in attributed):
            dropped += 1
            continue
        kept.append(fam)
    for i, fam in enumerate(kept, 1):
        fam.family_id = i
    return kept, dropped


def contain_cores(pending, ngrams, weight, start_id):
    """Cores of the second pass: leader assignment by containment, no size
    bucket, the shortest text leading so the purest copy of a letter leads
    the comments that carry it. Groups of one text are not cores."""
    items = [(t, ngrams[t], weight.get(t, 1)) for t in pending]
    groups = assign_leaders(items, CONTAIN_THRESHOLD, measure="containment",
                            shortest_first=True)
    out = []
    for leader, members in groups:
        if len(members) < 2:
            continue
        out.append(Family(family_id=start_id + len(out), core_kind="contain",
                          core=sorted(members), leaders=[leader]))
    return out


def _family_text(conn, ctx, families, ngrams, weight, comment_frequency, t0):
    """Family text and distinctive n-grams for these families, from the
    core; comment_frequency is fetched for the n-grams not already known.
    The exemplar is chosen later, from the members the core floor kept."""
    for fam in families:
        fam.ngrams, fam.family_text_min = family_text(fam.core, ngrams, weight)
    needed = set()
    for fam in families:
        needed.update(ng for ng in fam.ngrams if ng not in comment_frequency)
    needed_list = sorted(needed)
    for i in range(0, len(needed_list), _CHUNK):
        for ng, cf in conn.execute(ctx.render_sql(
                "SELECT ngram_id, comment_frequency FROM {analysis}.long_ngram_stats"
                " WHERE ngram_id IN (SELECT value FROM json_each(?))"), (json.dumps(needed_list[i:i + _CHUNK]),)):
            comment_frequency[ng] = cf
    for fam in families:
        fam.distinctive = distinctive_ngrams(fam.core, fam.ngrams, ngrams, weight,
                                             comment_frequency)
    _step(f"  family text: {sum(len(f.ngrams) for f in families):,} n-grams,"
          f" {sum(len(f.distinctive) for f in families):,} distinctive"
          f" over {len(families):,} families ({time.time() - t0:.0f}s)")


def _core_floor(families, ngrams, body_of, assigned):
    """Per unit: body-identical texts stay or leave together. The exemplar
    is chosen afterwards from what stayed: a contain core's shortest leader
    can leave at the floor when the texts that contain it share little
    among themselves, and six families on the third cutover run named an
    exemplar that was no longer a member."""
    left = 0
    for fam in families:
        for unit in units(fam.core, body_of):
            sets = [ngrams[c] for c in unit if c in ngrams]
            cov = unit_coverage(sets, fam.ngrams) if sets else (
                1.0 if fam.core_kind == "exact" else 0.0)
            for c in unit:
                if cov >= MEMBERSHIP_FLOOR:
                    fam.members[c] = Member(c, "core", cov)
                else:
                    assigned.pop(c, None)
                    left += 1
        if fam.members:
            fam.exemplar_id = choose_exemplar(sorted(fam.members), ngrams, weight_of(fam))
    _step(f"  core floor: {left:,} core text(s) left their family")


_WEIGHTS = {}


def weight_of(fam):
    """The weight map the build registered (set_weights), for exemplar
    choice inside the floor."""
    return _WEIGHTS


def set_weights(weight):
    _WEIGHTS.clear()
    _WEIGHTS.update(weight)


def _attach(families, ngrams, body_of, assigned):
    """Every text in no family joins the family whose distinctive n-grams
    cover the largest share of its own, at or above MEMBERSHIP_FLOOR; per
    unit, so body-identical texts move together."""
    index = {}
    by_id = {}
    for fam in families:
        by_id[fam.family_id] = fam
        for ng in fam.distinctive:
            index[ng] = fam.family_id
    attached = 0
    pending = [t for t in ngrams if t not in assigned]
    for unit in units(pending, body_of):
        total = 0
        hits = defaultdict(int)
        for c in unit:
            for ng in ngrams[c]:
                total += 1
                fid = index.get(ng)
                if fid is not None:
                    hits[fid] += 1
        if not hits:
            continue
        fid, n = max(hits.items(), key=lambda kv: (kv[1], -kv[0]))
        cov = n / total
        if cov >= MEMBERSHIP_FLOOR:
            fam = by_id[fid]
            for c in unit:
                fam.members[c] = Member(c, "attach", cov)
                assigned[c] = fam
                attached += 1
    _step(f"  attach: {attached:,} text(s) joined a family")


def _family_floor(families, assigned, weight, t0):
    """Families under FAMILY_MIN_COMMENTS dissolve and release their texts;
    the rest are renumbered 1..n."""
    kept = []
    released = 0
    for fam in families:
        if fam.members and fam.n_comments(weight) >= FAMILY_MIN_COMMENTS:
            kept.append(fam)
        else:
            for c in list(fam.members):
                assigned.pop(c, None)
                released += 1
            fam.members.clear()
    for i, fam in enumerate(kept, 1):
        fam.family_id = i
    n_campaign = sum(1 for f in kept if f.n_comments(weight) >= CAMPAIGN_MIN_COMMENTS)
    _step(f"  family floor: {released:,} text(s) released; families: {len(kept):,}"
          f" ({n_campaign:,} campaigns), {sum(f.n_texts for f in kept):,} texts,"
          f" {sum(f.n_comments(weight) for f in kept):,} comments ({time.time() - t0:.0f}s)")
    return kept


def _attribute_all(conn, ctx, families, survivors, weight):
    t0 = time.time()
    # Sentence keys from EVERY core text; the ones that are not survivors are
    # fetched here.
    need = set()
    for fam in families:
        need.update(c for c in fam.core if c not in survivors)
    texts = dict(survivors)
    need_list = sorted(need)
    for i in range(0, len(need_list), _CHUNK):
        for cid, text in conn.execute(ctx.render_sql(
                "SELECT comment_id, comment_text FROM {analysis}.v_source_comments"
                " WHERE comment_id IN (SELECT value FROM json_each(?))"), (json.dumps(need_list[i:i + _CHUNK]),)):
            texts[cid] = text or ""
    for fam in families:
        fam.sentence_counts = family_sentence_counts(fam.core, texts, weight)
        fam.sentence_keys = keys_at_threshold(fam.sentence_counts, fam.family_text_min)
    _step(f"  sentence keys: {sum(len(f.sentence_keys) for f in families):,}"
          f" over {len(need):,} fetched core texts ({time.time() - t0:.0f}s)")

    # The survivor members' occurrences, streamed once in id order.
    family_of = {}
    for fam in families:
        for c in fam.members:
            if c in survivors:
                family_of[c] = fam
    ids = sorted(family_of)
    done = 0
    with conn.cursor() as cur:
        cur.execute(ctx.render_sql(
            "SELECT comment_id, ngram_id, char_start, char_end"
            " FROM {analysis}.comment_long_ngrams WHERE comment_id IN (SELECT value FROM json_each(?))"
            " ORDER BY comment_id"), (json.dumps(ids),))
        current, occ = None, []

        def flush(cid, occ):
            fam = family_of[cid]
            attribute_member(fam.members[cid], survivors[cid], fam, occ)

        for cid, ng, a, b in cur:
            if cid != current:
                if current is not None:
                    flush(current, occ)
                    done += 1
                    if done % 10000 == 0:
                        _step(f"  attributed {done:,} of {len(ids):,} ({time.time() - t0:.0f}s)")
                current, occ = cid, []
            if a is None:
                raise SystemExit(
                    f"comment_long_ngrams has no offsets for {cid} — run"
                    " comments_db/scripts/extract_long_ngrams.py --rebuild first.")
            occ.append((ng, a, b))
        if current is not None:
            flush(current, occ)
    # Survivor members with no occurrence rows (under six tokens): tier 1 only.
    for cid in ids:
        m = family_of[cid].members[cid]
        if m.spans is None:
            flush(cid, [])
    _step(f"  attribution: {len(ids):,} survivor members ({time.time() - t0:.0f}s)")


def attribute_member(m, text, fam, occ):
    """One survivor member's attribution against its family, written onto
    the Member: the spans and totals from attribute(), and the own sentence
    keys the hourly step reads back."""
    (m.spans, m.shared_chars, m.own_chars, m.own_tokens, m.own_in_margin,
     m.has_own_text) = attribute(text, fam.sentence_keys, fam.ngrams, occ)
    m.own_keys = own_sentence_keys(text, m.spans)


# ------------------------------------------------------------------ write

def write(cur, ctx, families, weight):
    """Insert the five family tables. The caller owns the transaction and
    has emptied them (build_comment_groups.py --rebuild --write)."""
    id_map = {}
    for fam in families:
        n_comments = fam.n_comments(weight)
        row = cur.execute(ctx.render_sql(
            "INSERT INTO {analysis}.text_family (exemplar_comment_id, core_kind, n_texts,"
            " n_comments, is_campaign, family_text_min, params)"
            " VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING family_id"),
            (fam.exemplar_id, fam.core_kind, fam.n_texts, n_comments,
             n_comments >= CAMPAIGN_MIN_COMMENTS, fam.family_text_min, json.dumps(PARAMS))
        ).fetchone()
        assert row is not None
        id_map[fam.family_id] = row[0]
    cur.executemany(ctx.render_sql(
            "INSERT INTO {analysis}.text_family_ngram (family_id, ngram_id, n_core_texts, distinctive)"
            " VALUES (?, ?, ?, ?)"),
        [(id_map[fam.family_id], ng, n, ng in fam.distinctive)
         for fam in families for ng, n in fam.ngrams.items()])
    cur.executemany(ctx.render_sql(
            "INSERT INTO {analysis}.text_family_sentence (family_id, sentence_key, n_comments)"
            " VALUES (?, ?, ?)"),
        [(id_map[fam.family_id], key, n)
         for fam in families for key, n in fam.sentence_counts.items()])
    cur.executemany(ctx.render_sql(
            "INSERT INTO {analysis}.text_family_member (comment_id, family_id, joined_via, coverage,"
            " shared_chars, own_chars, own_tokens, own_in_margin, has_own_text,"
            " own_sentence_keys) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"),
        [(m.comment_id, id_map[fam.family_id], m.joined_via, m.coverage, m.shared_chars,
          m.own_chars, m.own_tokens, m.own_in_margin, m.has_own_text,
          json.dumps(m.own_keys) if m.own_keys is not None else None)
         for fam in families for m in fam.members.values()])
    cur.executemany(ctx.render_sql(
            "INSERT INTO {analysis}.text_family_span (comment_id, char_start, char_end, tier)"
            " VALUES (?, ?, ?, ?)"),
        [(m.comment_id, a, b, tier)
         for fam in families for m in fam.members.values() for a, b, tier in (m.spans or ())])
    return id_map


# --------------------------------------------------------------- dry run

R7_KEYS = (
    "these areas protect 354 municipal watersheds and supply drinking water",
    "roadless areas within the national forest system also contain all or part of 354",
)


def report(families, review, weight, survivors):
    """Printed whole: every review entry and every family, largest first
    (docs/reference/no-truncation.md). The run's output is the record."""
    print()
    if review:
        print(f"REVIEW — {len(review)} middle class(es) whose texts sat in two or more near"
              " cores; each joined those cores into one family (an identical body is the"
              " stronger evidence). All of them, with the leaders of the cores joined:")
        for mh, n, leaders in review:
            print(f"  middle {mh}: {n} comments joined cores led by {leaders}")
    else:
        print("review list: empty")
    print(f"\nfamilies, largest first ({len(families):,}):")
    for fam in sorted(families, key=lambda f: (-f.n_comments(weight), f.family_id)):
        n_surv = sum(1 for c in fam.members if c in survivors)
        n_own = sum(1 for c in fam.members if fam.members[c].has_own_text)
        print(f"  family {fam.family_id:>6} {fam.core_kind:<6} exemplar {fam.exemplar_id}"
              f"  texts {fam.n_texts:>7,}  comments {fam.n_comments(weight):>7,}"
              f"  survivors {n_surv:>6,}  with own text {n_own:>6,}")
    print("\nR7 — the watershed sentences, by key prefix:")
    for key in R7_KEYS:
        carriers = []
        for fam in families:
            for c, m in fam.members.items():
                if c not in survivors or not m.spans:
                    continue
                for a, b, tier in m.spans:
                    if shared_text.norm_sentence(survivors[c][a:b]).startswith(key):
                        carriers.append((c, fam.family_id, tier))
        non_members = [c for c, t in survivors.items()
                       if any(shared_text.norm_sentence(s).startswith(key)
                              for _a, _b, s in text_norm.sentences(t))
                       and not any(c == cc for cc, _f, _t in carriers)]
        print(f"  '{key}': the campaign's in {len(carriers)} member(s)"
              f" (families {sorted({f for _c, f, _t in carriers})}),"
              f" the signer's in {len(non_members)} comment(s)")
        for c, f, t in carriers:
            print(f"    member {c} family {f} tier {t}")
        for c in non_members:
            print(f"    signer {c}")


def main() -> None:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    add_project_argument(p)
    args = p.parse_args()
    ctx = context_from_args(args)
    with db.connect(**ctx.db_config) as conn:
        families, review, weight, survivors = build(conn, ctx)
    report(families, review, weight, survivors)
    print("\nDry run — nothing written. build_comment_groups.py --rebuild --write writes"
          " families and the partition together from this build.")


if __name__ == "__main__":
    main()
