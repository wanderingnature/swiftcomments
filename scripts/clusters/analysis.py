"""What the clustering cases share: the leader merge, the reduction, HDBSCAN,
the topic graph and cut, and the names.

Ported from eis-analysis scripts/model_free/analysis.py (renumber, centres,
laplacian, distinctive_terms; copied there from src/ledger/unit_cluster.py,
scripts/ledger/natural_k.py and scripts/ledger/topics_hdbscan.py) and
scripts/model_free/gate_clusters.py (leader_merge, the topic pass), with the
reductions of opening_umap.py and kind_clusters.py (UMAP 15 neighbours, 5
components, min_dist 0, cosine) and the PCA of opening_noise_passes.py (at
most one fewer component than rows). The seed is the case's, not a constant.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PCA_DIMS = 50
UMAP_NEIGHBORS = 15
UMAP_DIMS = 5
TOPIC_KNN = 5
MAX_TOPICS = 40


def code_version() -> tuple[str, int]:
    """The git commit the code is at, and 1 when tracked files have uncommitted changes."""
    try:
        head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--untracked-files=no"],
                               capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"a case is stamped with its git commit, and git could not give one here: {exc}."
                         " Run it in a git clone.") from None
    return head, int(bool(dirty))


def unit(V: np.ndarray) -> np.ndarray:
    return V / (np.linalg.norm(V, axis=1, keepdims=True) + 1e-9)


def leader_merge(V: np.ndarray, copies: np.ndarray, texts: list[str], thresh: float) -> np.ndarray:
    """Each row's leader index (itself for a leader). Most-copied first (ties by
    text), each unabsorbed row leads and absorbs every unabsorbed row at or above
    `thresh` cosine to it. `thresh` 0 is no merge."""
    n = len(V)
    if thresh <= 0:
        return np.arange(n)
    leader = np.full(n, -1)
    nbr: list[list[int]] = [[] for _ in range(n)]
    for a in range(0, n, 2048):
        r, c = np.nonzero(V[a:a + 2048] @ V.T >= thresh)
        for i, j in zip(r.tolist(), c.tolist()):
            if a + i != j:
                nbr[a + i].append(j)
    for i in sorted(range(n), key=lambda i: (-copies[i], texts[i])):
        if leader[i] >= 0:
            continue
        leader[i] = i
        for j in nbr[i]:
            if leader[j] < 0:
                leader[j] = i
    return leader


def reduce(V: np.ndarray, how: str, seed: int) -> np.ndarray:
    """PCA to 50 (at most one fewer than the rows) or UMAP to 5 on cosine."""
    if how == "pca50":
        from sklearn.decomposition import PCA
        return PCA(min(PCA_DIMS, len(V) - 1), random_state=seed).fit_transform(V)
    if how == "umap5":
        import umap
        return umap.UMAP(n_neighbors=UMAP_NEIGHBORS, n_components=UMAP_DIMS, min_dist=0.0, metric="cosine",
                         random_state=seed).fit_transform(V)
    raise ValueError(f"unknown reduction {how!r}")


def hdbscan(P: np.ndarray, min_cluster_size: int, min_samples: int, selection: str) -> np.ndarray:
    """HDBSCAN's labels, -1 for noise."""
    from sklearn.cluster import HDBSCAN
    return HDBSCAN(min_cluster_size=min_cluster_size, min_samples=min_samples,
                   cluster_selection_method=selection, n_jobs=-1, copy=True).fit(P).labels_


def renumber(raw: np.ndarray) -> np.ndarray:
    """Labels as 0 for noise and 1.. by cluster size, largest first."""
    order = sorted(set(raw.tolist()) - {-1}, key=lambda c: (-int((raw == c).sum()), c))
    m = {c: i + 1 for i, c in enumerate(order)}
    return np.array([m.get(int(c), 0) for c in raw], dtype=np.int64)


def laplacian(X: np.ndarray, knn: int = TOPIC_KNN):
    """Eigenvalues and eigenvectors of the normalized Laplacian of the mutual knn-NN cosine graph."""
    from sklearn.neighbors import kneighbors_graph
    n = len(X)
    Xn = X / np.linalg.norm(X, axis=1, keepdims=True)
    A = kneighbors_graph(Xn, min(knn, n - 1), metric="cosine", mode="distance").toarray()
    W = np.where(A > 0, np.clip(1 - A, 1e-6, None), 0.0)
    W = np.maximum(W, W.T)
    d = W.sum(1)
    d[d == 0] = 1e-9
    L = np.eye(n) - W / np.sqrt(np.outer(d, d))
    return np.linalg.eigh(L)


def topics(centroids: np.ndarray, k: int | None) -> tuple[np.ndarray, list[tuple[int, float]]]:
    """The clusters grouped into topics: the mean direction of the centroids
    removed, average linkage on cosine distance, cut at `k` or the largest
    eigengap (k from 2, over the first 40 eigenvalues). Returns each cluster's
    topic index (0..) and the eigengap candidates, largest first. Four or fewer
    clusters have no graph to read: each is its own topic unless `k` says."""
    from sklearn.cluster import AgglomerativeClustering
    n = len(centroids)
    if n == 0:
        return np.zeros(0, dtype=np.int64), []
    if n == 1:
        return np.zeros(1, dtype=np.int64), []
    C = centroids - centroids.mean(0)
    C = C / (np.linalg.norm(C, axis=1, keepdims=True) + 1e-9)
    gaps: list[tuple[int, float]] = []
    if n > 3:
        ev, _ = laplacian(C)
        d = np.diff(ev[:min(len(ev), MAX_TOPICS)])
        gaps = sorted(((i + 1, float(d[i])) for i in range(1, len(d))), key=lambda x: -x[1])
    cut = min(k or (gaps[0][0] if gaps else n), n)
    lab = AgglomerativeClustering(n_clusters=cut, metric="precomputed", linkage="average").fit_predict(1 - C @ C.T)
    return lab.astype(np.int64), gaps


def distinctive_terms(L: np.ndarray, texts: np.ndarray, order: list[int], top: int = 8) -> list[list[str]]:
    """Class-based tf-idf: each class one document; the terms most specific to it.
    A class with no countable word gets no terms."""
    import scipy.sparse as sp
    from sklearn.feature_extraction.text import CountVectorizer
    docs = [" ".join(texts[i] for i in np.where(L == c)[0]) for c in order]
    cv = CountVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2,
                         token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z\-]{2,}\b")
    try:
        X = sp.csr_matrix(cv.fit_transform(docs))
    except ValueError:  # no term in two classes: nothing is distinctive
        return [[] for _ in order]
    terms = np.array(cv.get_feature_names_out())
    sums = np.asarray(X.sum(1))
    tf = np.asarray(X.todense()) / np.where(sums == 0, 1, sums)
    df = X.getnnz(axis=0)
    ctfidf = tf * np.log(1 + len(order) / df)
    return [terms[np.argsort(ctfidf[k])[::-1][:top]].tolist() if sums[k, 0] else [] for k in range(len(order))]
