#!/usr/bin/env python3
"""The clustering cases: steps 12 to 14, the clusters, the topics and their names.

    uv run python scripts/clusters/cases.py run [--sentences opening|opening+hits|all] [--view comment|plain|topic]
        [--merge 0.98] [--top D] [--reduction pca50|umap5] [--min-cluster-size N] [--min-samples N]
        [--selection eom|leaf] [--structure all|by-kind|by-prong] [--noise-passes N] [--k N] [--seed N] [--model M]
    uv run python scripts/clusters/cases.py list
    uv run python scripts/clusters/cases.py compare CASE_A CASE_B
    uv run python scripts/clusters/cases.py choose CASE [--note TEXT]
    uv run python scripts/clusters/cases.py remeasure
    uv run python scripts/clusters/cases.py concern-map CASE [--note TEXT]
    make clusters [SENTENCES=... VIEW=... MERGE=... TOP=... REDUCTION=... MCS=... MS=... SELECTION=... STRUCTURE=... PASSES=... K=... SEED=...]
    make cases
    make compare-cases A=<case> B=<case>
    make choose CASE=<case> [NOTE="..."]
    make concern-map CASE=<case> [NOTE="..."]

The steps are code with no model call, so their choices are run as cases and
compared, not decided beforehand. A case is one value on each axis:

    sentences   opening: the sentences that open the gate alone; opening+hits: and the sentences that
                hold a whole-comment gate hit; all: every sentence of the gate-open comments
    view        the vectors read (make embed VIEW=)
    merge       near-copies at this cosine or more collapsed into one leader first, most-copied
                first; 0 for none
    top         all-but-the-top: the mean of the case's vectors removed, the top D principal
                components removed, unit length again, before the merge; 0 for the centring
                alone; unset for no correction
    reduction   pca50 (PCA to 50), umap5 (UMAP to 5: 15 neighbours, min_dist 0, cosine)
                or pacmap5 (PaCMAP to 5: 10 neighbours, angular)
    HDBSCAN     min_cluster_size, min_samples, selection eom or leaf
    structure   all: one clustering; by-kind: one clustering for each gate kind (LAW, EVID, GAP, ALT)
                over the leaders of that kind, the topics then drawn across the kinds; by-prong: one
                clustering for each prong gate (impacts, significance, alternatives, compliance) over
                the leaders whose sentences open it
    noise       passes in which the noise of the pass before is clustered again on its own, a fresh
                reduction fitted to it, until a pass finds no cluster
    k           the topic cut; none: the largest eigengap
    seed        the seed of the reduction

The defaults: the gate-opening sentences, the comment view, no merge, UMAP, HDBSCAN 10/10
eom, one clustering, no noise pass, the cut at the largest eigengap, seed 0.

Steps 13 and 14: one centroid for each cluster, the mean direction of the
centroids removed, average linkage on cosine distance, cut at the largest
eigengap of the normalized Laplacian of the 5-nearest-neighbour graph of the
centroids (the candidates are kept); each topic and cluster named by its eight
most distinctive words and bigrams (class-based tf-idf), each cluster shown by
its two sentences nearest its centroid.

A case's name is made from its values, the embedding model among them, so the
same settings on two models' vectors are two cases. Its run replaces its rows in the five
cluster_case tables and no other case's; the case row keeps its values, its
git commit, the sentence build it read and its measures.

The sentences come from gate_sentence, the vectors from sentence_embedding, every
setting an argument, every result in the file.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1]))
sys.path.insert(0, str(_HERE.parents[2]))

from shared import case_compare, db  # noqa: E402
from clusters import analysis as an  # noqa: E402
from clusters.embed import VIEWS, unpack  # noqa: E402

KINDS = ("LAW", "EVID", "GAP", "ALT")
PRONGS = ("impacts", "significance", "alternatives", "compliance")
SENTENCES = {"opening": "o.opens = 1", "opening+hits": "(o.opens = 1 OR o.holds_hit = 1)", "all": "1 = 1"}
TABLES = ("cluster_case", "cluster_case_leader", "cluster_case_member", "cluster_case_cluster", "cluster_case_topic")


def choose(conn, case_name: str, note: str | None) -> str:
    """Record the case as the choice of its embedding model; a new choice replaces the old.
    Returns the model."""
    row = conn.execute("SELECT model FROM cluster_case WHERE case_name = ?", (case_name,)).fetchone()
    if row is None:
        raise SystemExit(f"no case {case_name!r}: make cases lists them")
    with conn.transaction():
        conn.execute("INSERT OR REPLACE INTO cluster_case_choice (model, case_name, note, chosen_at)"
                     " VALUES (?, ?, ?, ?)",
                     (row[0], case_name, note, datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return row[0]


def concern_map(conn, case_name: str, note: str | None) -> None:
    """Record the case as the concern map: stage 5 decides between the choices of stage 4, so
    the case has to be one of them. A new decision replaces the old."""
    chosen = {r[0] for r in conn.execute("SELECT case_name FROM cluster_case_choice")}
    if case_name not in chosen:
        raise SystemExit(f"{case_name!r} is not a choice of stage 4: choose a case for each model first (make choose)")
    with conn.transaction():
        conn.execute("INSERT OR REPLACE INTO cluster_concern_map (one, case_name, note, decided_at)"
                     " VALUES (1, ?, ?, ?)",
                     (case_name, note, datetime.now(timezone.utc).isoformat(timespec="seconds")))


def model_slug(model: str) -> str:
    """The model's name as a part of a case name: its last path part, lower case, letters and digits."""
    return re.sub(r"[^a-z0-9]+", "-", model.rsplit("/", 1)[-1].lower()).strip("-")


def case_name(a: argparse.Namespace) -> str:
    """The case's name from its values; `a.model` is the resolved embedding model."""
    merge = f"m{int(round(a.merge * 100))}" if a.merge > 0 else "m0"
    return (f"{a.sentences}.{a.view}.{model_slug(a.model)}.{merge}.{a.reduction}"
            f".{a.min_cluster_size}-{a.min_samples}-{a.selection}"
            f".{a.structure}.p{a.noise_passes}.k{a.k or 'auto'}.s{a.seed}"
            + (f".top{a.top}" if a.top is not None else ""))


def resolve_model(conn, view: str, model: str | None) -> str:
    instruction = VIEWS[view]
    found = [r[0] for r in conn.execute(
        "SELECT DISTINCT model FROM sentence_embedding WHERE instruction = ? ORDER BY model", (instruction,))]
    if model:
        if model not in found:
            raise SystemExit(f"no vector under view {view} by model {model}; the models with one: {found or 'none'}")
        return model
    if not found:
        raise SystemExit(f"no vector under view {view}: run make embed VIEW={view}")
    if len(found) > 1:
        raise SystemExit(f"vectors under view {view} by {len(found)} models ({', '.join(found)}): name one with --model")
    return found[0]


def load(conn, sentences: str, view: str, model: str):
    """The case's distinct sentences: keys, texts, occurrences (of the occurrences the
    case reads), kinds (4 booleans), significance (a GAP sentence of a GAP-3 comment),
    and unit vectors."""
    rows = conn.execute(
        "SELECT o.text_key, count(*) AS n, max(o.law), max(o.evid), max(o.gap), max(o.alt),"
        " max(CASE WHEN o.gap = 1 AND ss.gap >= 3 THEN 1 ELSE 0 END), s.text"
        " FROM gate_sentence_occurrence o JOIN gate_sentence s USING (text_key)"
        " LEFT JOIN substance_scores ss USING (comment_id)"
        f" WHERE {SENTENCES[sentences]} GROUP BY o.text_key ORDER BY o.text_key").fetchall()
    if not rows:
        raise SystemExit("no sentence to cluster: run make sentences first")
    keys = [r[0] for r in rows]
    vec = {r[0]: r[1] for r in conn.execute(
        "SELECT text_key, vector FROM sentence_embedding WHERE model = ? AND instruction = ?",
        (model, VIEWS[view]))}
    missing = [k for k in keys if k not in vec]
    if missing:
        raise SystemExit(f"{len(missing):,} of the case's {len(keys):,} sentences have no vector under view {view}"
                         f" by {model}: run make embed VIEW={view}")
    V = an.unit(np.vstack([unpack(vec[k]) for k in keys]).astype(np.float32))
    return (keys, [r[7] for r in rows], np.array([r[1] for r in rows], dtype=np.int64),
            np.array([[r[2], r[3], r[4], r[5]] for r in rows], dtype=bool),
            np.array([r[6] for r in rows], dtype=bool), V)


def coverage(conn, clustered_keys: set[str]) -> tuple[int, int, int, int]:
    """The gate-open comments, those not covered, the gate-opening sentence occurrences, and those in
    a cluster. A comment is covered when one of its substantive sentences (it opens the gate alone,
    or it holds a whole-comment gate hit) is a clustered sentence. A clustered subject line or
    thank-you line does not cover a comment."""
    comments: dict[str, bool] = {}
    opening = opening_in = 0
    for cid, key, opens, holds in conn.execute(
            "SELECT comment_id, text_key, opens, holds_hit FROM gate_sentence_occurrence"):
        inside = key in clustered_keys
        comments[cid] = comments.get(cid, False) or (inside and bool(opens or holds))
        if opens:
            opening += 1
            opening_in += int(inside)
    return len(comments), sum(1 for v in comments.values() if not v), opening, opening_in


def remeasure(conn) -> list[tuple[str, int, int]]:
    """Every stored case's coverage counted again from its stored rows, with no case run again.
    Returns (case, the old count of comments not covered, the new count)."""
    out = []
    for (name,) in conn.execute("SELECT case_name FROM cluster_case ORDER BY case_name").fetchall():
        keys = {k for (k,) in conn.execute(
            "SELECT l.text_key FROM cluster_case_leader l JOIN cluster_case_member m"
            " ON m.case_name = l.case_name AND m.leader_key = l.leader_key"
            " WHERE l.case_name = ? AND m.cluster > 0", (name,))}
        old = conn.execute("SELECT comments_unclustered FROM cluster_case WHERE case_name = ?", (name,)).fetchone()[0]
        _, uncovered, opening, opening_in = coverage(conn, keys)
        with conn.transaction():
            conn.execute("UPDATE cluster_case SET comments_unclustered = ?, opening_occurrences = ?,"
                         " opening_occurrences_clustered = ? WHERE case_name = ?",
                         (uncovered, opening, opening_in, name))
        out.append((name, old, uncovered))
    return out


def cluster_group(LV: np.ndarray, a: argparse.Namespace) -> list[tuple[int, np.ndarray]]:
    """The clusters of one group of leaders: (pass, the row indices of each cluster).
    The first pass, then the noise clustered again, pass by pass."""
    out: list[tuple[int, np.ndarray]] = []
    remaining = np.arange(len(LV))
    for p in range(1, a.noise_passes + 2):
        floor = max(a.min_cluster_size, {"umap5": an.UMAP_NEIGHBORS, "pacmap5": an.PACMAP_NEIGHBORS}.get(a.reduction, 1))
        if len(remaining) <= floor:
            break
        lab = an.renumber(an.hdbscan(an.reduce(LV[remaining], a.reduction, a.seed),
                                     a.min_cluster_size, a.min_samples, a.selection))
        if lab.max() == 0:
            break
        for c in range(1, int(lab.max()) + 1):
            out.append((p, remaining[lab == c]))
        remaining = remaining[lab == 0]
    return out


def run_case(conn, a: argparse.Namespace) -> dict:
    t0 = time.time()
    model = a.model = resolve_model(conn, a.view, a.model)
    name = case_name(a)
    srun = conn.execute("SELECT max(run_id) FROM gate_sentence_run").fetchone()[0]
    keys, texts, occ, kinds, sig, V = load(conn, a.sentences, a.view, model)
    top_variance = None
    if a.top is not None:
        V, shares = an.all_but_the_top(V, a.top)
        top_variance = json.dumps(shares)
    leader = an.leader_merge(V, occ, texts, a.merge)
    lead = np.flatnonzero(leader == np.arange(len(keys)))
    pos = {int(i): j for j, i in enumerate(lead)}
    L_occ = np.bincount(leader, weights=occ, minlength=len(keys)).astype(np.int64)[lead]
    L_var = (np.bincount(leader, minlength=len(keys)) - 1)[lead]
    L_kinds = np.zeros((len(lead), 4), dtype=bool)
    L_sig = np.zeros(len(lead), dtype=bool)
    for i, li in enumerate(leader):
        L_kinds[pos[int(li)]] |= kinds[i]
        L_sig[pos[int(li)]] |= sig[i]
    LV, L_texts = V[lead], np.array([texts[i] for i in lead], dtype=object)

    if a.structure == "all":
        groups = [("", np.arange(len(lead)))]
    elif a.structure == "by-kind":
        groups = [(k, np.flatnonzero(L_kinds[:, j])) for j, k in enumerate(KINDS)]
    else:
        # KINDS order is LAW, EVID, GAP, ALT; a prong holds the leaders whose
        # sentences open it (impacts: GAP or EVID; significance: a GAP sentence
        # of a GAP-3 comment; alternatives: ALT; compliance: LAW)
        L_prongs = np.stack([L_kinds[:, 1] | L_kinds[:, 2], L_sig,
                             L_kinds[:, 3], L_kinds[:, 0]], axis=1)
        groups = [(p, np.flatnonzero(L_prongs[:, j])) for j, p in enumerate(PRONGS)]
    found: list[tuple[str, int, np.ndarray]] = []           # (kind, pass, leader rows)
    for kind, rows in groups:
        for p, members in cluster_group(LV[rows], a):
            found.append((kind, p, rows[members]))
    found.sort(key=lambda f: (-len(f[2]), f[0], int(f[2].min())))
    cents = []
    for _, _, m in found:
        c = LV[m].mean(0)
        cents.append(c / np.linalg.norm(c))
    C = np.array(cents) if cents else np.zeros((0, LV.shape[1]))
    t_lab, gaps = an.topics(C, a.k)
    # topics ordered by occurrences, largest first
    t_occ = {t: sum(int(L_occ[found[i][2]].sum()) for i in range(len(found)) if t_lab[i] == t) for t in set(t_lab.tolist())}
    t_order = {t: n + 1 for n, t in enumerate(sorted(t_occ, key=lambda t: (-t_occ[t], t)))}

    # names: one row per (leader, cluster) and per (leader, topic)
    pair_l = np.concatenate([m for _, _, m in found]) if found else np.zeros(0, dtype=np.int64)
    pair_c = np.concatenate([np.full(len(m), i + 1) for i, (_, _, m) in enumerate(found)]) if found else np.zeros(0)
    c_terms = an.distinctive_terms(pair_c, L_texts[pair_l], list(range(1, len(found) + 1))) if found else []
    t_pairs = sorted({(int(l), t_order[int(t_lab[int(c) - 1])]) for l, c in zip(pair_l, pair_c)})
    tl = np.array([t for _, t in t_pairs])
    t_terms = an.distinctive_terms(tl, L_texts[np.array([l for l, _ in t_pairs], dtype=np.int64)],
                                   list(range(1, len(t_order) + 1))) if t_pairs else []

    clustered = np.zeros(len(lead), dtype=bool)
    for _, _, m in found:
        clustered[m] = True
    key_clustered = {keys[i] for i in range(len(keys)) if clustered[pos[int(leader[i])]]}
    gate_comments, uncovered, opening, opening_in = coverage(conn, key_clustered)
    head, dirty = an.code_version()
    m = {"case_name": name, "model": model, "sentence_run_id": srun, "input_sentences": len(keys),
         "occurrences": int(occ.sum()), "leaders": len(lead), "clusters": len(found), "topics": len(t_order),
         "eigengaps": json.dumps(gaps[:10]), "leaders_clustered": int(clustered.sum()),
         "occurrences_clustered": int(L_occ[clustered].sum()),
         "largest_cluster": max((len(f[2]) for f in found), default=0),
         "gate_comments": gate_comments, "comments_unclustered": uncovered,
         "opening_occurrences": opening, "opening_occurrences_clustered": opening_in}

    with conn.transaction():
        for t in TABLES:
            conn.execute(f"DELETE FROM {t} WHERE case_name = ?", (name,))
        conn.execute(
            "INSERT INTO cluster_case VALUES (" + ",".join("?" * 33) + ")",
            (name, a.sentences, a.view, model, a.merge, a.reduction, a.min_cluster_size, a.min_samples, a.selection,
             a.structure, a.noise_passes, a.k, a.seed, srun, head, dirty,
             datetime.now(timezone.utc).isoformat(timespec="seconds"), round(time.time() - t0, 1),
             m["input_sentences"], m["occurrences"], m["leaders"], m["clusters"], m["topics"], m["eigengaps"],
             m["leaders_clustered"], m["occurrences_clustered"], m["largest_cluster"], m["gate_comments"],
             m["comments_unclustered"], m["opening_occurrences"], m["opening_occurrences_clustered"],
             a.top, top_variance))
        conn.executemany("INSERT INTO cluster_case_leader VALUES (?,?,?)",
                         [(name, keys[i], keys[int(leader[i])]) for i in range(len(keys))])
        member = {}
        for kind, rows in groups:
            for r in rows:
                member[(int(r), kind)] = 0
        for i, (kind, _, mm) in enumerate(found):
            for r in mm:
                member[(int(r), kind)] = i + 1
        conn.executemany("INSERT INTO cluster_case_member VALUES (?,?,?,?)",
                         [(name, keys[int(lead[r])], kind, c) for (r, kind), c in sorted(member.items())])
        crow = []
        for i, (kind, p, mm) in enumerate(found):
            cos = LV[mm] @ C[i]
            share = L_kinds[mm].mean(0)
            near = mm[np.argsort(-cos)[:2]]
            crow.append((name, i + 1, kind, p, t_order[int(t_lab[i])], len(mm), int(L_var[mm].sum()),
                         int(L_occ[mm].sum()), round(float(cos.mean()), 4), *[round(float(x), 4) for x in share],
                         json.dumps(c_terms[i]), json.dumps([str(L_texts[j]) for j in near])))
        conn.executemany("INSERT INTO cluster_case_cluster VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", crow)
        trow = []
        for t, n in sorted(t_order.items(), key=lambda x: x[1]):
            idx = [i for i in range(len(found)) if t_lab[i] == t]
            ls = np.unique(np.concatenate([found[i][2] for i in idx]))
            trow.append((name, n, len(idx), len(ls), int(sum(int(L_occ[found[i][2]].sum()) for i in idx)),
                         json.dumps(t_terms[n - 1])))
        conn.executemany("INSERT INTO cluster_case_topic VALUES (?,?,?,?,?,?)", trow)
    m["seconds"] = round(time.time() - t0, 1)
    return m


def cmd_run(a: argparse.Namespace) -> int:
    if a.merge < 0 or a.merge >= 1:
        raise SystemExit("--merge is a cosine below 1, or 0 for none")
    if a.top is not None and a.top < 0:
        raise SystemExit("--top is 0 or more: the components removed, 0 for the centring alone")
    conn = db.connect(db.DB_PATH)
    a.model = resolve_model(conn, a.view, a.model)
    print(f"make clusters: case {case_name(a)}", flush=True)
    m = run_case(conn, a)
    conn.close()
    print(f"done in {m['seconds']}s: {m['input_sentences']:,} sentences ({m['occurrences']:,} occurrences),"
          f" {m['leaders']:,} leaders; {m['clusters']:,} clusters, {m['topics']:,} topics;"
          f" {m['leaders_clustered']:,} leaders clustered ({m['leaders_clustered'] / max(1, m['leaders']):.0%}),"
          f" largest cluster {m['largest_cluster']:,}; {m['comments_unclustered']:,} of {m['gate_comments']:,}"
          f" gate-open comments with no sentence in a cluster; {m['opening_occurrences_clustered']:,} of"
          f" {m['opening_occurrences']:,} gate-opening sentences in a cluster")
    return 0


def cmd_list(_a: argparse.Namespace) -> int:
    conn = db.connect(db.DB_PATH)
    rows = conn.execute(
        "SELECT case_name, clusters, topics, leaders, leaders_clustered, largest_cluster, comments_unclustered,"
        " gate_comments, opening_occurrences_clustered, opening_occurrences, created_at FROM cluster_case"
        " ORDER BY created_at").fetchall()
    conn.close()
    if not rows:
        print("no case yet: make clusters")
        return 0
    for r in rows:
        print(f"{r[0]}: {r[1]} clusters, {r[2]} topics; {r[4]:,} of {r[3]:,} leaders clustered, largest {r[5]:,};"
              f" {r[6]:,} of {r[7]:,} comments with no sentence in a cluster; {r[8]:,} of {r[9]:,} gate-opening"
              f" sentences clustered; {r[10]}")
    return 0


def cmd_compare(a: argparse.Namespace) -> int:
    conn = db.connect(db.DB_PATH)
    m = case_compare.compare(case_compare.labels(conn, a.first), case_compare.labels(conn, a.second))
    terms = {}
    for name in (a.first, a.second):
        terms[name] = {c: json.loads(t) for c, t in conn.execute(
            "SELECT cluster, terms FROM cluster_case_cluster WHERE case_name = ?", (name,))}
    conn.close()
    agree = (f"adjusted Rand {m['ari']}, NMI {m['nmi']}" if m["ari"] is not None
             else "too few sentences clustered by both to compare")
    print(f"first  {a.first}\nsecond {a.second}\n"
          f"{m['shared_sentences']:,} sentences in both ({m['only_first']:,} only in the first,"
          f" {m['only_second']:,} only in the second); clustered by the first {m['clustered_first']:,},"
          f" by the second {m['clustered_second']:,}, by both {m['clustered_both']:,},"
          f" by neither {m['clustered_neither']:,}\non the sentences both cluster: {agree}\n"
          f"clusters of the first with 80% or more of their sentences in one cluster of the second:"
          f" {m['clusters_80']} of {len(m['crossing'])}; median share {m['median_share']}")
    for r in m["crossing"]:
        print(f"  {r['cluster']:>4} ({r['sentences']} sentences; {', '.join(terms[a.first].get(r['cluster'], [])[:4])})"
              f" -> {r['best_second']} at {r['share']:.0%} ({', '.join(terms[a.second].get(r['best_second'], [])[:4])});"
              f" {r['noise_in_second']} noise in the second")
    return 0


def cmd_remeasure(_a: argparse.Namespace) -> int:
    conn = db.connect(db.DB_PATH)
    rows = remeasure(conn)
    conn.close()
    print(f"make cases-remeasure: {len(rows)} cases; comments not covered, counted on substantive sentences:")
    for name, old, new in rows:
        print(f"  {old:>6,} -> {new:>6,}  {name}")
    return 0


def cmd_choose(a: argparse.Namespace) -> int:
    conn = db.connect(db.DB_PATH)
    model = choose(conn, a.case, a.note)
    chosen = conn.execute("SELECT model, case_name FROM cluster_case_choice ORDER BY model").fetchall()
    conn.close()
    print(f"make choose: {a.case} is the choice for {model}")
    for m, c in chosen:
        print(f"  {m}: {c}")
    return 0


def cmd_concern_map(a: argparse.Namespace) -> int:
    conn = db.connect(db.DB_PATH)
    concern_map(conn, a.case, a.note)
    conn.close()
    print(f"make concern-map: {a.case} is the concern map")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--sentences", choices=sorted(SENTENCES), default="opening")
    r.add_argument("--view", choices=sorted(VIEWS), default="comment")
    r.add_argument("--model", help="the embedding model, when vectors of more than one are in the file")
    r.add_argument("--merge", type=float, default=0.0, help="leader-merge cosine; 0 for none")
    r.add_argument("--top", type=int, default=None,
                   help="all-but-the-top: components removed from the vectors before the merge;"
                        " 0 for the centring alone (default: no correction)")
    r.add_argument("--reduction", choices=("pca50", "umap5", "pacmap5"), default="umap5")
    r.add_argument("--min-cluster-size", type=int, default=10)
    r.add_argument("--min-samples", type=int, default=10)
    r.add_argument("--selection", choices=("eom", "leaf"), default="eom")
    r.add_argument("--structure", choices=("all", "by-kind", "by-prong"), default="all")
    r.add_argument("--noise-passes", type=int, default=0)
    r.add_argument("--k", type=int, help="the topic cut (default: the largest eigengap)")
    r.add_argument("--seed", type=int, default=0)
    r.set_defaults(fn=cmd_run)
    ls = sub.add_parser("list")
    ls.set_defaults(fn=cmd_list)
    cp = sub.add_parser("compare", help="two cases: how far they group the same sentences the same way")
    cp.add_argument("first")
    cp.add_argument("second")
    cp.set_defaults(fn=cmd_compare)
    rm = sub.add_parser("remeasure", help="count every stored case's coverage again from its stored rows")
    rm.set_defaults(fn=cmd_remeasure)
    ch = sub.add_parser("choose", help="record a case as the choice of its embedding model")
    ch.add_argument("case")
    ch.add_argument("--note", help="why it was chosen")
    ch.set_defaults(fn=cmd_choose)
    cm = sub.add_parser("concern-map", help="record one of the two choices as the concern map (stage 5)")
    cm.add_argument("case")
    cm.add_argument("--note", help="why it was decided")
    cm.set_defaults(fn=cmd_concern_map)
    a = ap.parse_args(argv)
    return int(a.fn(a))


if __name__ == "__main__":
    sys.exit(main())
