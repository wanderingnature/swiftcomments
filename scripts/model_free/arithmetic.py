"""Strength, gate, band; the roll-up from sentences to the comment; the
answerability rating. The definitions are the guide's (steps 7 and 9 of
docs/guides/how-we-score-in-plain-english.md), implemented here and not
imported from v3."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import DIMS, GATE_DIMS
from .detectors import SentenceScore

BANDS = ((0, 5, "minimal"), (6, 11, "marginal"), (12, 17, "developed"), (18, 99, "strong"))


def strength_of(dims: dict[str, int]) -> int:
    return sum(dims[d] for d in DIMS)


def gate_basis(dims: dict[str, int]) -> list[str]:
    return [d for d in GATE_DIMS if dims[d] >= 2]


def band_of(strength: int) -> str:
    for lo, hi, name in BANDS:
        if lo <= strength <= hi:
            return name
    raise ValueError(f"strength out of range: {strength}")


@dataclass
class CommentScore:
    comment_id: str
    dims: dict[str, int]
    strength: int
    gate: bool
    gate_basis: list[dict[str, int | str]]
    band: str
    moves: list[str]
    targets: list[str]
    sentence_count: int
    opening_unit: dict[str, int] = field(default_factory=dict)
    has_citation: bool = False
    mechanism: bool = False


def roll_up(comment_id: str, sentences: list[SentenceScore]) -> CommentScore:
    """Each dimension is the maximum over the comment's sentences; the gate
    basis names the first sentence that reached each gate dimension's maximum."""
    if not sentences:
        raise ValueError(f"no sentences for {comment_id}")
    dims = {d: max(s.dims[d] for s in sentences) for d in DIMS}
    opening: dict[str, int] = {}
    for d in DIMS:
        for s in sorted(sentences, key=lambda x: x.start_char):
            if s.dims[d] == dims[d] and dims[d] > 0:
                opening[d] = s.unit_id
                break
    basis = [{"dimension": d, "unit_id": opening[d]} for d in gate_basis(dims)]
    strength = strength_of(dims)
    moves = sorted({m for s in sentences for m in s.moves})
    targets = sorted({t for s in sentences for t in s.targets})
    return CommentScore(
        comment_id=comment_id, dims=dims, strength=strength, gate=bool(basis),
        gate_basis=basis, band=band_of(strength), moves=moves, targets=targets,
        sentence_count=len(sentences), opening_unit=opening,
        has_citation=any(s.has_citation for s in sentences),
        mechanism=any(s.mechanism for s in sentences))


# ---------------------------------------------------------- answerability

NO_ACTION_CODES = [
    "alternative_eliminated", "addressed_in_analysis", "deferred_to_site_specific",
    "misinterpreted", "not_required", "policy_preference_noted",
    "no_cause_effect", "outside_scope", "certified_not_substantive",
]
NO_TEXT_ONLY_TEST = {"alternative_eliminated", "deferred_to_site_specific",
                     "not_required", "policy_preference_noted"}
MECHANISM_MOVES = {"M1", "M3", "M5"}
MECHANISM_TARGETS = {"T1", "T2"}


@dataclass
class Answerability:
    comment_id: str
    level: str
    defeated: list[dict[str, int | str]]
    open: list[str]
    mechanism: bool
    cite: bool


def rate(c: CommentScore) -> Answerability:
    """Which of the nine no-action dispositions the comment defeats, and the
    level that falls out of that set. Each defeated code names the dimension
    and the sentence that defeated it."""
    d = c.dims
    limb1 = d["GAP"] == 2 or d["EVID"] >= 2
    limb2 = d["GAP"] == 3
    limb3 = d["ALT"] >= 2
    limb4 = d["LAW"] == 2
    gated = bool(c.gate_basis)
    mv = set(c.moves) & MECHANISM_MOVES
    tg = set(c.targets) & MECHANISM_TARGETS
    mechanism = bool(mv and tg)
    cite = d["DOC"] >= 2 or c.has_citation
    form = d["PLACE"] >= 2 or d["DOC"] >= 2

    defeated: list[dict[str, int | str]] = []
    if gated:
        if limb4:
            defeated.append({"code": "addressed_in_analysis", "dimension": "LAW", "unit_id": c.opening_unit["LAW"]})
            defeated.append({"code": "certified_not_substantive", "dimension": "LAW", "unit_id": c.opening_unit["LAW"]})
        nce_dim: str | None = None
        if limb4:
            nce_dim = "LAW"
        elif limb2:
            nce_dim = "GAP"
        elif limb3:
            nce_dim = "ALT"
        elif limb1 and mechanism and cite:
            nce_dim = "GAP" if d["GAP"] == 2 else "EVID"
        if nce_dim is not None:
            defeated.append({"code": "no_cause_effect", "dimension": nce_dim, "unit_id": c.opening_unit[nce_dim]})
        if form:
            fdim = "DOC" if d["DOC"] >= 2 else "PLACE"
            for code in ("outside_scope", "misinterpreted"):
                defeated.append({"code": code, "dimension": fdim, "unit_id": c.opening_unit[fdim]})
    codes = {str(x["code"]) for x in defeated}
    still_open = [code for code in NO_ACTION_CODES if code not in codes]
    if not gated:
        level = "A0"
    elif "addressed_in_analysis" in codes:
        level = "A1"
    elif "no_cause_effect" in codes:
        level = "A2"
    else:
        level = "A3"
    return Answerability(c.comment_id, level, defeated, still_open, mechanism, cite)
