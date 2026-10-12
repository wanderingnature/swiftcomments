"""Leader assignment in the near-duplicate detector: no chaining, fixed order.

No DB, no LLM. assign_leaders replaced union-find on 2026-09-20
(docs/design/shared-text-families-implementation.md, section 5.1). The case
that matters: A overlaps B and B overlaps C, but A does not overlap C.
Union-find merged all three; leader assignment keeps every member within the
threshold of its leader.

The module is loaded by path: comments_db/src and the repo's top-level src
are both packages named `src`.

    uv run pytest tests/substance/test_leader_assignment.py
"""
import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

_spec = importlib.util.spec_from_file_location(
    "detect_duplicates_incremental",
    _REPO_ROOT / "comments_db" / "scripts" / "detect_duplicates_incremental.py")
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
assign_leaders = _mod.assign_leaders

THRESHOLD = 0.85


def _chain():
    """Three 100-n-gram sets: A and B share 90, B and C share 90, A and C share 80."""
    a = set(range(0, 100))
    b = set(range(10, 110))          # A & B = 90 of 100
    c = set(range(20, 120))          # B & C = 90 of 100, A & C = 80 of 100
    return a, b, c


def _members(groups):
    return {leader: set(members) for leader, members in groups}


def test_chain_is_not_merged():
    a, b, c = _chain()
    items = [("A", a, 1), ("B", b, 1), ("C", c, 1)]
    groups = assign_leaders(items, THRESHOLD)
    by_leader = _members(groups)
    # Order: equal weight and size, so comment_id: A leads; B joins A (0.90);
    # C is 0.80 to A, under the threshold, so C leads its own group.
    assert by_leader == {"A": {"A", "B"}, "C": {"C"}}


def test_every_member_is_within_threshold_of_its_leader():
    a, b, c = _chain()
    items = [("A", a, 1), ("B", b, 1), ("C", c, 1), ("D", set(range(5, 105)), 1)]
    sets = dict((cid, s) for cid, s, _w in items)
    for leader, members in assign_leaders(items, THRESHOLD):
        for m in members:
            overlap = len(sets[m] & sets[leader]) / min(len(sets[m]), len(sets[leader]))
            assert overlap >= THRESHOLD or m == leader, (leader, m, overlap)


def test_order_is_deterministic_under_permutation():
    a, b, c = _chain()
    items = [("A", a, 1), ("B", b, 1), ("C", c, 1)]
    first = assign_leaders(items, THRESHOLD)
    second = assign_leaders(list(reversed(items)), THRESHOLD)
    assert first == second


def test_heavier_text_leads():
    a, b, _c = _chain()
    items = [("A", a, 1), ("B", b, 500)]
    assert _members(assign_leaders(items, THRESHOLD)) == {"B": {"A", "B"}}


def test_seeded_representatives_lead_first():
    a, b, _c = _chain()
    items = [("A", a, 500), ("B", b, 1)]
    assert _members(assign_leaders(items, THRESHOLD, seeded={"B"})) == {"B": {"A", "B"}}


def test_text_joins_the_leader_it_overlaps_most():
    lead1 = set(range(0, 100))
    lead2 = set(range(200, 300))
    x = set(range(5, 100)) | set(range(200, 205))     # 95 with lead1, 5 with lead2
    items = [("L1", lead1, 10), ("L2", lead2, 10), ("X", x, 1)]
    assert _members(assign_leaders(items, THRESHOLD)) == {"L1": {"L1", "X"}, "L2": {"L2"}}


def test_empty_bucket():
    assert assign_leaders([], THRESHOLD) == []


def test_a_cluster_expands_only_its_leaders_group():
    """Two stored representatives that land in one cluster: the cluster's new
    comments join the leader's group, not both. On 2026-09-21 the store added
    them to every matching group and 949 comments sat in two."""
    sys.path.insert(0, str(_REPO_ROOT / "comments_db" / "scripts"))
    import detect_duplicates_incremental as det  # pyright: ignore[reportMissingImports]
    representatives = {10: "R1", 20: "R2"}
    assert det.expansion_target("R1", ["R1", "R2"], representatives) == 10
    assert det.expansion_target("R2", ["R1", "R2"], representatives) == 20
    assert det.expansion_target("N1", ["R2"], representatives) == 20
    assert det.expansion_target("N1", [], representatives) is None
