"""Two clustering cases side by side (new): how far they group the same
sentences the same way. Read by `make compare-cases` (scripts/clusters/cases.py
compare) and the console's Topics page, so both give the same figures.

A sentence's cluster in a case is its leader's (cluster_case_leader,
cluster_case_member); 0 is noise. In a by-kind case a leader of two kinds is in
two clusters, and the lower-numbered (the larger) is taken.

    agreement   on the sentences both cases cluster: the adjusted Rand index (1 the same
                partition, 0 what chance gives) and the normalized mutual information
    crossing    for each cluster of the first case, the cluster of the second that holds
                most of its sentences, and the share it holds
"""
from __future__ import annotations

from collections import Counter

import numpy as np


def labels(conn, case_name: str) -> dict[str, int]:
    """{text_key: cluster} for every sentence the case read."""
    member: dict[str, int] = {}
    for leader, cluster in conn.execute(
            "SELECT leader_key, cluster FROM cluster_case_member WHERE case_name = ?", (case_name,)):
        cur = member.get(leader, 0)
        member[leader] = cluster if cur == 0 else (min(cur, cluster) if cluster else cur)
    rows = conn.execute("SELECT text_key, leader_key FROM cluster_case_leader WHERE case_name = ?", (case_name,))
    out = {k: member.get(l, 0) for k, l in rows}
    if not out:
        raise SystemExit(f"no case {case_name!r}: make cases lists them")
    return out


def compare(a: dict[str, int], b: dict[str, int]) -> dict:
    """The figures of two cases' labels: counts, agreement, and the crossing."""
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    keys = sorted(set(a) & set(b))
    x = np.array([a[k] for k in keys])
    y = np.array([b[k] for k in keys])
    both = (x > 0) & (y > 0)
    out = {"shared_sentences": len(keys), "only_first": len(set(a) - set(b)), "only_second": len(set(b) - set(a)),
           "clustered_first": int((x > 0).sum()), "clustered_second": int((y > 0).sum()),
           "clustered_both": int(both.sum()), "clustered_neither": int(((x == 0) & (y == 0)).sum()),
           "ari": None, "nmi": None, "crossing": []}
    if both.sum() >= 2:
        out["ari"] = round(float(adjusted_rand_score(x[both], y[both])), 4)
        out["nmi"] = round(float(normalized_mutual_info_score(x[both], y[both])), 4)
    by_first: dict[int, Counter] = {}
    for xi, yi in zip(x, y):
        if xi > 0:
            by_first.setdefault(int(xi), Counter())[int(yi)] += 1
    for c in sorted(by_first):
        counts = by_first[c]
        n = sum(counts.values())
        clustered = Counter({k: v for k, v in counts.items() if k > 0})
        best, held = clustered.most_common(1)[0] if clustered else (0, 0)
        out["crossing"].append({"cluster": c, "sentences": n, "noise_in_second": counts.get(0, 0),
                                "best_second": best, "share": round(held / n, 4)})
    shares = [r["share"] for r in out["crossing"]]
    out["clusters_80"] = sum(1 for s in shares if s >= 0.8)
    out["median_share"] = round(float(np.median(shares)), 4) if shares else None
    return out
