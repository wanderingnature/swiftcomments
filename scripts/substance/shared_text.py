#!/usr/bin/env python3
"""The shared-content layer — what text a comment actually contributed.

ONE implementation of "what is boilerplate", used by the mechanical screen
(mechanical_screens.py) and by the scoring queue (score_comments.py), so the
question has exactly one answer everywhere in the pipeline.

A campaign's organizer writes a letter; thousands of people sign it, many
adding a sentence of their own. Exact-hash dedup calls every one of those
UNIQUE (the added sentence changes the hash), so the pipeline used to score
the organizer's letter thousands of times and credit each signer with the
organizer's citations. This module measures the same thing mechanically:

  boilerplate span  a sentence (>= MIN_SENT_CHARS, normalized) appearing in
                    >= BOILER_K distinct comments of the corpus
  own text          the comment MINUS its boilerplate spans — the submitter's
                    own contribution, and the only text the model is shown
  cluster           majority-shared comments (>= MAJORITY_SHARED of their
                    long-sentence characters are boilerplate) keyed by their
                    top-CLUSTER_KEY_SENTENCES boilerplate sentences
  exemplar          the member of a cluster carrying the most boilerplate —
                    its shared text is scored ONCE for the whole cluster

Population is the floor-filter survivors ({analysis}.substance_floor WHERE
NOT floored), not the scored set: the screen and the queue both run BEFORE
scoring now, and the corpus frequencies must not depend on what has been
paid for yet.

Deterministic, no model calls. See docs/design/rescore-queue-design.md.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# The normal forms and the splitter live in shared.text_norm since 2026-09-20,
# where the n-gram extractor reads the same rules (one normalizer, R2). They
# are re-exported here because sixteen call sites, three scripts and two test
# files reach them as shared_text.<name>.
from shared.text_norm import (  # noqa: E402,F401
    norm_key, norm_sentence, sentences, unescape_text)

BOILER_K = 10              # sentence in >= K distinct comments == boilerplate
MIN_SENT_CHARS = 40        # shorter sentences never suppress anything real
MAJORITY_SHARED = 0.5      # >= this share of long-sentence chars == a member
EXEMPLAR_MIN_MEMBERS = 10  # smaller clusters get their own calls (orphans)
CLUSTER_KEY_SENTENCES = 3

# The family constants (docs/design/shared-text-families.md, decided 2026-09-20;
# docs/design/shared-text-families-implementation.md, section 2). families.py
# builds with them, load_shapes reads what it built, and the shadow run
# compares that against the method-1 constants above.
FAMILY_MIN_COMMENTS = 3     # a family exists at this many comments (copies counted)
CAMPAIGN_MIN_COMMENTS = 10  # the `campaign` label; gates no scoring
MEMBERSHIP_FLOOR = 0.5      # share of a text's n-grams in family text to be a member
# Family text and family sentences are what FAMILY_MIN_COMMENTS comments of the
# core share, copies counted: thresholds name a number of comments, not a share
# of the core, because a share moves with corpus size (owner, 2026-09-20).
DISTINCTIVE_SHARE = 0.80    # distinctive: this share of an n-gram's weighted occurrences in one family
SENTENCE_COVERAGE = 0.75    # tier 2: a sentence covered this much by family text is the campaign's
TRIVIAL_OWN_TOKENS = 10     # own text under this, all in the first or last line: no delta item
MIN_OWN_CHARS = 50          # own text under this many characters, anywhere: no delta item —
                            # too short to carry substance; not worth a scoring call
EXEMPLAR_SAMPLE = 300       # members sampled for mean Jaccard when no text repeats
CONTAIN_THRESHOLD = 0.6     # second pass: containment (shared over the smaller set) to group texts in no family
SECOND_PASS_MIN_SHARED = 6  # a text enters the second pass with this many n-grams shared by FAMILY_MIN_COMMENTS+ comments


@dataclass
class Shape:
    """One comment's shared/own split.

    Two builders fill it with one contract. `analyze` (method 1) decides the
    shared side by corpus sentence frequency and leaves `family_id` and
    `is_member` unset, so `majority_shared` is the character-share rule.
    `load_shapes` (families) reads the stored attribution: the shared side is
    the family's text, `is_member` says whether the comment is in a family,
    and `majority_shared` means exactly that."""
    comment_id: str
    text: str
    boiler_spans: list = field(default_factory=list)   # [(start, end)]
    own_text: str = ""
    shared_text: str = ""
    own_chars: int = 0
    shared_chars: int = 0
    cluster_key: tuple = ()
    family_id: int | None = None
    is_member: bool | None = None
    tiers: dict = field(default_factory=dict)          # (start, end) -> 1 | 2

    @property
    def shared_fraction(self):
        total = self.own_chars + self.shared_chars
        return self.shared_chars / total if total else 0.0

    @property
    def majority_shared(self):
        if self.is_member is not None:
            return self.is_member
        return self.shared_fraction >= MAJORITY_SHARED

    def in_boilerplate(self, pos):
        """Is this character offset inside a boilerplate sentence?"""
        return any(a <= pos < b for a, b in self.boiler_spans)


def load_shapes(conn, render_sql):
    """One Shape per floor survivor, from the stored family attribution
    (text_family_member and text_family_span, written by
    build_comment_groups.py --write from families.build).

    The shared side of a member is exactly its stored sentence spans; the
    rest is the signer's. A non-member survivor has no spans and all of its
    text is its own. No short-sentence exception: a copied `Thank you.` is
    the campaign's because the family says so (tier 1), and a short own
    sentence in the body counts as own text.

    Refuses to run before the partition exists: the screen and the queue
    would otherwise read an empty attribution and call every survivor a
    non-member."""
    rows = load_corpus(conn, render_sql)
    (n_families,) = conn.execute(render_sql(
        "SELECT count(*) FROM {analysis}.text_family")).fetchone()
    if not n_families:
        raise SystemExit(
            "text_family is empty — run"
            " scripts/substance/build_comment_groups.py --rebuild --write first."
            " The attribution is decided there; nothing can read it before.")
    members = {cid: (fid, own) for cid, fid, own in conn.execute(render_sql(
        "SELECT comment_id, family_id, has_own_text"
        " FROM {analysis}.text_family_member"))}
    spans = {}
    for cid, a, b, tier in conn.execute(render_sql(
            "SELECT comment_id, char_start, char_end, tier"
            " FROM {analysis}.text_family_span")):
        spans.setdefault(cid, {})[(a, b)] = tier

    shapes = {}
    for cid, text in rows:
        sh = Shape(comment_id=cid, text=text or "")
        member = members.get(cid)
        sh.family_id = member[0] if member else None
        sh.is_member = member is not None
        stored = spans.get(cid, {})
        own_parts, shared_parts = [], []
        for a, b, s in sentences(sh.text):
            tier = stored.get((a, b))
            if tier is not None:
                sh.boiler_spans.append((a, b))
                sh.tiers[(a, b)] = tier
                sh.shared_chars += len(s)
                shared_parts.append(s)
            else:
                sh.own_chars += len(s)
                own_parts.append(s)
        sh.own_text = "\n".join(p.strip() for p in own_parts if p.strip())
        sh.shared_text = "\n".join(p.strip() for p in shared_parts if p.strip())
        shapes[cid] = sh
    return shapes


def analyze(rows):
    """[(comment_id, text)] -> {comment_id: Shape}. Two passes: corpus-wide
    sentence frequency, then the per-comment split."""
    rows = [(cid, text or "") for cid, text in rows]
    freq = {}
    spans = {}
    for cid, text in rows:
        ss = sentences(text)
        spans[cid] = ss
        # Length is measured on the NORMALIZED sentence: markup is not content,
        # and a span that is mostly '<br/>' is not a 40-character sentence.
        for key in {k for k in (norm_sentence(s) for _a, _b, s in ss)
                    if len(k) >= MIN_SENT_CHARS}:
            freq[key] = freq.get(key, 0) + 1

    shapes = {}
    for cid, text in rows:
        sh = Shape(comment_id=cid, text=text)
        own_parts, shared_parts, bkeys = [], [], []
        for a, b, s in spans[cid]:
            key = norm_sentence(s)
            long_enough = len(key) >= MIN_SENT_CHARS
            if long_enough and freq.get(key, 0) >= BOILER_K:
                sh.boiler_spans.append((a, b))
                sh.shared_chars += len(s)
                shared_parts.append(s)
                bkeys.append(key)
            else:
                # Short sentences are never boilerplate (they are not counted
                # at all), so they stay with the submitter's own text.
                if long_enough:
                    sh.own_chars += len(s)
                own_parts.append(s)
        sh.own_text = "\n".join(p.strip() for p in own_parts if p.strip())
        sh.shared_text = "\n".join(p.strip() for p in shared_parts if p.strip())
        sh.cluster_key = tuple(sorted(bkeys)[:CLUSTER_KEY_SENTENCES])
        shapes[cid] = sh
    return shapes


@dataclass
class Cluster:
    key: tuple
    members: list
    exemplar_id: str

    @property
    def size(self):
        return len(self.members)


def clusters(shapes, min_members=EXEMPLAR_MIN_MEMBERS):
    """Shared-content clusters big enough to carry an exemplar.

    Returns (clusters_by_key, orphan_ids): majority-shared comments whose
    cluster is smaller than min_members are ORPHANS — nothing to inherit
    from, so they are scored on their own text like any unique comment.
    """
    by_key = {}
    for sh in shapes.values():
        if sh.majority_shared:
            by_key.setdefault(sh.cluster_key, []).append(sh.comment_id)
    out, orphans = {}, []
    for key, members in by_key.items():
        if len(members) < min_members:
            orphans.extend(members)
            continue
        # The exemplar carries the most boilerplate — its shared text is the
        # campaign's text with the least of any one signer's own writing in
        # it. comment_id breaks ties so the choice is reproducible.
        exemplar = max(sorted(members),
                       key=lambda c: shapes[c].shared_chars)
        out[key] = Cluster(key=key, members=sorted(members),
                           exemplar_id=exemplar)
    return out, sorted(orphans)


def citation_scopes(conn, render_sql, shapes):
    """{comment_id: {'own': bool, 'shared': bool}} — where each comment's
    MECHANICALLY confirmed legal-authority citations sit.

    comment_authorities stores matched_text, not offsets, so a citation is
    located the way the screen locates it (first occurrence in the text).
    This is what keeps the organizer's citation from confirming LAW for
    every signer: a citation inside a boilerplate span is the CAMPAIGN's,
    and scores on the campaign's exemplar, not on the signer.
    """
    hits = {}
    for cid, mt in conn.execute(render_sql(
            "SELECT comment_id, matched_text"
            " FROM {analysis}.comment_authorities")):
        hits.setdefault(cid, []).append(mt or "")
    out = {}
    for cid, matches in hits.items():
        sh = shapes.get(cid)
        if sh is None:
            continue
        scope = {"own": False, "shared": False}
        for mt in matches:
            if not mt:
                continue
            i = sh.text.find(mt)
            if i < 0:
                scope["own"] = True  # not locatable — keep the pipeline's word
            elif sh.in_boilerplate(i):
                scope["shared"] = True
            else:
                scope["own"] = True
        out[cid] = scope
    return out


def load_corpus(conn, render_sql):
    """The screened/scored population: floor-filter survivors with text."""
    return conn.execute(render_sql(
        "SELECT f.comment_id, v.comment_text"
        " FROM {analysis}.substance_floor f"
        " JOIN {analysis}.v_source_comments v USING (comment_id)"
        " WHERE NOT f.floored"
        " ORDER BY f.comment_id")).fetchall()
