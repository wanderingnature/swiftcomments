"""Near-duplicate grouping by leader assignment, shared by the detector
(comments_db/scripts/detect_duplicates_incremental.py, resemblance inside
size buckets) and the family build (scripts/substance/families.py, the
second pass by containment over the texts in no family).

Two measures over n-gram id sets, both Broder's (1997):

  resemblance   |A & B| / min(|A|, |B|) inside a bucket of equal size, where
                it behaves as the Jaccard index; the detector's first pass
  containment   |A & B| / min(|A|, |B|) across any sizes: a letter carried
                inside a longer personal comment is contained in it

A Bloom filter over each set screens pairs before the exact intersection
(Bloom 1970); its estimate is of the same measure as the exact check, so a
short text inside a long one is not screened out by a low bit-Jaccard.

Leader assignment (Hartigan 1975): texts are visited in a fixed order, each
is compared to the leaders so far and joins the one it overlaps most at or
above the threshold, or becomes a leader. Every member is therefore within
the threshold of its own leader; connected components over the pairs would
let A join C through B whether or not A resembles C.
"""

from typing import Dict, List, Optional, Set, Tuple

import mmh3
from bitarray import bitarray


class SimpleBloomFilter:
    """Simple Bloom filter for fast similarity pre-filtering."""

    def __init__(self, ngram_ids: Set[int], size: Optional[int] = None):
        if size is None:
            # Size based on number of items for ~1% false positive rate
            self.size = max(1024, len(ngram_ids) * 10)
        else:
            self.size = size
        self.bits = bitarray(self.size)
        self.bits.setall(0)
        self.num_hashes = 3
        for ngram_id in ngram_ids:
            for i in range(self.num_hashes):
                self.bits[mmh3.hash(str(ngram_id), i) % self.size] = 1
        self.count = self.bits.count()

    def similarity(self, other: "SimpleBloomFilter") -> float:
        """Jaccard of the bit arrays: the resemblance estimate."""
        if self.size != other.size:
            return 0.0
        intersection = (self.bits & other.bits).count()
        union = (self.bits | other.bits).count()
        return intersection / union if union else 0.0

    def containment(self, other: "SimpleBloomFilter") -> float:
        """Intersection over the smaller bit count: the containment estimate."""
        if self.size != other.size:
            return 0.0
        smaller = min(self.count, other.count)
        return (self.bits & other.bits).count() / smaller if smaller else 0.0


def assign_leaders(items: List[Tuple[str, Set[int], int]], threshold: float,
                   seeded: Optional[Set[str]] = None, bloom_size: Optional[int] = None,
                   measure: str = "resemblance",
                   shortest_first: bool = False) -> List[Tuple[str, Set[str]]]:
    """Leader clustering over texts.

    items: (id, n-gram id set, weight) per text, weight being the text's
    exact-class size. Order: `seeded` ids first (stored representatives),
    then weight descending, then n-gram count descending (or ascending with
    shortest_first, so the purest copy of a letter leads the texts that
    contain it), then id. Each text joins the leader with the highest exact
    overlap at or above the threshold; ties go to the earlier leader. The
    exact overlap is intersection over the smaller set for both measures;
    `measure` chooses the Bloom estimate that screens pairs first.

    Returns [(leader_id, members)] in leader order, members including the
    leader. Deterministic for a given input and threshold.
    """
    seeded = seeded or set()
    sign = 1 if shortest_first else -1
    order = sorted(items, key=lambda it: (it[0] not in seeded, -it[2], sign * len(it[1]), it[0]))
    if not order:
        return []
    if bloom_size is None:
        bloom_size = max(1024, max(len(it[1]) for it in order) * 10)
    estimate = (SimpleBloomFilter.containment if measure == "containment"
                else SimpleBloomFilter.similarity)
    leaders: List[Tuple[str, Set[int], SimpleBloomFilter, Set[str]]] = []
    for cid, ngrams, _weight in order:
        bloom = SimpleBloomFilter(ngrams, size=bloom_size)
        best = None
        best_overlap = 0.0
        for leader in leaders:
            if estimate(leader[2], bloom) < threshold * 0.7:
                continue
            smaller = min(len(ngrams), len(leader[1]))
            if smaller == 0:
                continue
            overlap = len(ngrams & leader[1]) / smaller
            if overlap >= threshold and overlap > best_overlap:
                best, best_overlap = leader, overlap
        if best is None:
            leaders.append((cid, ngrams, bloom, {cid}))
        else:
            best[3].add(cid)
    return [(leader[0], leader[3]) for leader in leaders]


def group_sets(sets: Dict[str, Set[int]]) -> List[Tuple[str, Set[str]]]:
    """Convenience for tests: leader assignment over {id: set} at 0.85."""
    return assign_leaders([(k, v, 1) for k, v in sets.items()], 0.85)
