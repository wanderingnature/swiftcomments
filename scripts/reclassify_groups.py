#!/usr/bin/env python3
"""Re-classify every unique comment group with the active prompt, recoverably.

One call per comment group (canonical text >= MIN_COMMENT_LENGTH), sent to the
model server of .env.

- Every response is committed to {analysis}.classification_run_items the moment it
  arrives, whole, before anything is loaded from it.
- Every CHUNK stored responses, one transaction loads them: each group's members'
  active rows are replaced by the group's new result (load_classifications.replace_groups).
- A restart (--resume) loads what was stored but not loaded, then sends only the
  groups with no stored call. No stored response is paid for twice.
- One log, logs/reclassify_<run_id>.log: a line per call, a block per chunk, the
  client's retry diagnostics, nothing cut.

    python scripts/reclassify_groups.py --project roadless --new-run --concurrency 16
    python scripts/reclassify_groups.py --project roadless --new-run --limit 200
        (a pilot: 200 groups sent, stored and loaded, then exit; --resume sends the rest)
    python scripts/reclassify_groups.py --project roadless --resume <run_id>
    python scripts/reclassify_groups.py --project roadless --resume <run_id> --retry-errors
    python scripts/reclassify_groups.py --project roadless --runs
        (every run so far, what each loaded, and the command that continues the latest)

    make stance LIMIT=200                      a new run, the first 200 groups
    make stance-runs                           the runs and the command to continue
    make stance RUN=<run_id> LIMIT=200         the next 200 of that run
    make stance RUN=<run_id> CONCURRENCY=32    the rest of it

A --limit counts within the run it is given: a resumed run skips every group the
run has an item for and sends the next N; a --new-run starts from the first group
again. The client keeps at most --concurrency calls in flight and lowers that on
its own when the server answers 429 (shared/llm_client.py).

Reads and writes data/roadless.sqlite through shared/db.py; the model server from
.env (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, LLM_PROVIDER).
"""

import argparse
import json
import signal
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime
from pathlib import Path

import requests

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from generate_batch_fromfile import MIN_COMMENT_LENGTH, _clean_text  # noqa: E402
from load_classifications import _aggregate, replace_groups  # noqa: E402
from parse_multi_batch_results import classification_rows, parse_completion  # noqa: E402
from shared import db  # noqa: E402
from shared.instrument import configured_model, model_of  # noqa: E402
from shared.llm_client import ChatClient, EndpointNotReady, thinking_off  # noqa: E402
from shared.project_context import ProjectContext  # noqa: E402
from src.pipeline.profile import ProjectProfile, sentiment_topic_response_format  # noqa: E402

_STRENGTHS = ("HIGH", "MEDIUM", "LOW")
_MIN_TOPIC_CONFIDENCE = 0.7   # load_classifications' threshold, counted per call here
# Refused for every call alike (key, credits, the provider pin): abort, don't grind.
_ABORT_STATUS = (401, 402, 403)


class Abort(RuntimeError):
    """A failure every remaining call would repeat."""


class RunLog:
    """The run's one log: appended, flushed per line, echoed to the console."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._f = open(path, "a", encoding="utf-8", buffering=1)
        self._lock = threading.Lock()

    def __call__(self, msg: str) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = str(msg).split("\n")
        text = "\n".join([f"{stamp} {lines[0]}"] + [f"  {ln}" for ln in lines[1:]])
        with self._lock:
            self._f.write(text + "\n")
            self._f.flush()
            print(text, flush=True)

    def diag(self, msg: str) -> None:
        """ChatClient's retry / slow-call diagnostics."""
        self(f"[llm] {msg}")


class Run:
    def __init__(self, ctx, profile, run_id, run_ts, concurrency, chunk_size, log,
                 limit=None):
        self.ctx = ctx
        self.limit = limit            # groups to send this session (a pilot), or None
        self.profile = profile
        self.run_id = run_id
        self.run_ts = run_ts
        self.concurrency = concurrency
        self.chunk_size = chunk_size
        self.log = log
        # The server and the model of .env; the client keeps at most `concurrency`
        # calls in flight and lowers that itself when the server answers 429.
        self.client = ChatClient(log=log.diag, max_in_flight=concurrency)
        self.model = self.client.model
        self.model_stamp = model_of(self.model)
        self.topic_names = {t["topic_name"] for t in profile.topics}
        self.stopping = False
        self.total = 0                # eligible groups
        self.done_before = 0          # loaded + errored when this session started
        # SQLite has one writer: the workers return each reply and the
        # main loop stores it through this one connection.
        self._conn = None
        self._n_sent = 0

    # ------------------------------------------------------------ db helpers

    def sql(self, text):
        return self.ctx.render_sql(text)

    def _store_conn(self):
        if self._conn is None:
            self._conn = db.connect(**self.ctx.db_config)
        return self._conn

    def close(self):
        if self._conn is not None:
            self._conn.close()

    # ------------------------------------------------------------ selection

    def eligible_groups(self):
        """Every group whose canonical text is long enough, in group_id order."""
        with db.connect(**self.ctx.db_config) as conn:
            return conn.execute(self.sql(
                "SELECT g.group_id, c.comment_id, c.comment_text"
                " FROM {analysis}.comment_group g"
                " JOIN {analysis}.v_source_comments c ON c.comment_id = g.canonical_comment_id"
                " WHERE length(c.comment_text) >= ? ORDER BY g.group_id"),
                (MIN_COMMENT_LENGTH,)).fetchall()

    def latest_items(self):
        """{group_id: (attempt, status)} — each group's highest attempt."""
        with db.connect(**self.ctx.db_config) as conn:
            rows = conn.execute(self.sql(
                "SELECT group_id, attempt, status FROM ("
                "  SELECT group_id, attempt, status,"
                "         row_number() OVER (PARTITION BY group_id ORDER BY attempt DESC) AS rn"
                "  FROM {analysis}.classification_run_items WHERE run_id = ?)"
                " WHERE rn = 1 ORDER BY group_id"), (self.run_id,)).fetchall()
        return {g: (a, s) for g, a, s in rows}

    # ------------------------------------------------------------ one call

    def _body(self, comment_text):
        params = self.profile.model_parameters
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.profile.system_prompt},
                {"role": "user",
                 "content": self.profile.render_user_prompt(_clean_text(comment_text))},
            ],
            "temperature": params.get("temperature", 0.0),
            "top_p": params.get("top_p", 1.0),
            "response_format": sentiment_topic_response_format(),
        }
        return thinking_off(body, self.model, self.client.base_url)

    def _judge(self, comment_id, payload):
        """(status, error_kind, error_detail, classification) for one response."""
        choices = payload.get("choices") or []
        finish = choices[0].get("finish_reason") if choices else None
        if finish != "stop":
            usage = payload.get("usage") or {}
            return ("error", "truncated",
                    f"finish_reason={finish} completion_tokens="
                    f"{usage.get('completion_tokens')} — full response stored", None)
        classification, err = parse_completion(comment_id, payload)
        if err is not None:
            return ("error", "unparseable",
                    f"{err['error_message']}\n{err.get('ai_response', '')}", None)
        assert classification is not None
        stance = classification["sentiment"].strip().upper()
        strength = classification["sentiment_strength"].strip().upper()
        if stance not in self.profile.sentiment_map or strength not in _STRENGTHS:
            return ("error", "invalid_sentiment",
                    f"sentiment {classification['sentiment']}|"
                    f"{classification['sentiment_strength']}", None)
        topics = classification["topics"]
        if not isinstance(topics, list) or not all(isinstance(t, dict) for t in topics):
            return ("error", "unparseable", f"topics is not a list of objects: {topics!r}",
                    None)
        unknown = sorted({str(t.get("topic_name")) for t in topics} - self.topic_names)
        if unknown:
            return ("error", "unknown_topic", f"topic name(s) not in the taxonomy: {unknown}",
                    None)
        for t in topics:
            conf = t.get("confidence")
            if not isinstance(conf, (int, float)) or not 0.0 <= conf <= 1.0:
                return ("error", "unparseable",
                        f"topic {t.get('topic_name')} confidence {conf!r} is not in 0..1",
                        None)
        return "received", None, None, classification

    def call(self, group_id, comment_id, comment_text, attempt):
        """Send one group (a worker) and return its outcome for store(). Raises Abort."""
        t0 = time.monotonic()
        payload = None
        status, kind, detail, classification = "error", "transport", "no response", None
        try:
            payload = self.client.post(self._body(comment_text))
        except EndpointNotReady as exc:
            raise Abort(f"g={group_id} c={comment_id}: {exc}") from None
        except requests.ConnectionError as exc:
            # No route to the endpoint after the client's retries: every call would
            # end the same way.
            raise Abort(f"g={group_id} c={comment_id}: {exc}") from None
        except requests.RequestException as exc:
            resp = getattr(exc, "response", None)
            code = resp.status_code if resp is not None else None
            if code in _ABORT_STATUS:
                raise Abort(f"g={group_id} c={comment_id}: HTTP {code} {exc}") from None
            status, kind, detail, classification = "error", "transport", str(exc), None
        if payload is not None:
            try:
                status, kind, detail, classification = self._judge(comment_id, payload)
            except Exception as exc:
                # A shape _judge did not foresee: the paid response is still stored.
                import traceback
                status, kind, classification = "error", "unparseable", None
                detail = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        seconds = time.monotonic() - t0
        return (group_id, comment_id, comment_text, attempt, status, kind, detail,
                classification, payload, seconds)

    def store(self, group_id, comment_id, comment_text, attempt, status, kind, detail,
              classification, payload, seconds):
        """Store one call's outcome (committed) on the main thread, and log it."""
        usage = (payload or {}).get("usage") or {}
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
        finish = None
        if payload and payload.get("choices"):
            finish = payload["choices"][0].get("finish_reason")
        conn = self._store_conn()
        conn.execute(self.sql(
            "INSERT INTO {analysis}.classification_run_items"
            " (run_id, group_id, attempt, comment_id, status, error_kind, error_detail,"
            "  finish_reason, prompt_tokens, cached_tokens, completion_tokens, cost,"
            "  seconds, response)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"),
            (self.run_id, group_id, attempt, comment_id, status, kind, detail, finish,
             usage.get("prompt_tokens"), cached, usage.get("completion_tokens"),
             usage.get("cost"), round(seconds, 3),
             json.dumps(payload) if payload is not None else None))
        conn.commit()

        self._n_sent += 1
        n = self.done_before + self._n_sent
        head = (f"[{n:>7,}/{self.total:,}] g={group_id} c={comment_id}"
                f" len={len(comment_text):,}")
        if status == "error":
            tail = f"ERROR {kind} {seconds:.2f}s — {detail}"
            if payload is not None:
                tail += (f" | in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')}"
                         f" ${usage.get('cost')} — response stored")
            self.log(f"{head} {tail}")
            return
        assert classification is not None
        topics = classification["topics"]
        low = sum(1 for t in topics if t["confidence"] < _MIN_TOPIC_CONFIDENCE)
        bare = sum(1 for t in topics if t["confidence"] >= _MIN_TOPIC_CONFIDENCE
                   and t.get("topic_name") != "sentiment_only"
                   and not [p for p in (t.get("supporting_phrases") or []) if str(p).strip()])
        names = ",".join(str(t["topic_name"]) for t in topics)
        extra = ""
        if low or bare:
            extra = f" | not loaded: {low} below {_MIN_TOPIC_CONFIDENCE}, {bare} without phrases"
        self.log(f"{head} {seconds:.2f}s in={usage.get('prompt_tokens')} cached={cached}"
                 f" out={usage.get('completion_tokens')} ${usage.get('cost')} {finish}"
                 f" {classification['sentiment']}|{classification['sentiment_strength']}"
                 f" {len(topics)} topics [{names}]{extra}")

    # ------------------------------------------------------------ load

    def load_received(self):
        """Load every stored, not-yet-loaded response of the run in one transaction.
        Returns (groups loaded, member rows written)."""
        with db.connect(**self.ctx.db_config) as conn:
            with conn.transaction():
                items = conn.execute(self.sql(
                    "SELECT group_id, attempt, comment_id, response"
                    " FROM {analysis}.classification_run_items"
                    " WHERE run_id = ? AND status = 'received' ORDER BY group_id"),
                    (self.run_id,)).fetchall()
                if not items:
                    return 0, 0
                rows = []
                for group_id, _attempt, comment_id, response in items:
                    classification, err = parse_completion(comment_id, json.loads(response))
                    if err is not None or classification is None:
                        raise RuntimeError(
                            f"stored response for g={group_id} c={comment_id} no longer"
                            f" parses: {err}")
                    rows.extend(classification_rows(classification))
                comments, topics, _ = _aggregate(rows, self.profile.sentiment_map)
                group_ids = [g for g, _, _, _ in items]
                class_id, _n_topics, n_members = replace_groups(
                    conn, self.ctx, group_ids, comments, topics, self.run_id,
                    self.model_stamp)
                conn.cursor().executemany(self.sql(
                    "UPDATE {analysis}.classification_run_items"
                    " SET status = 'loaded', loaded_at = CURRENT_TIMESTAMP, classification_id = ?"
                    " WHERE run_id = ? AND group_id = ? AND attempt = ?"),
                    [(class_id[c], self.run_id, g, a) for g, a, c, _ in items])
        return len(items), n_members

    def progress(self, chunk_no, loaded, members, t_block, n_block, t_session):
        latest = (
            "WITH latest AS (SELECT group_id, status, error_kind FROM ("
            "   SELECT group_id, status, error_kind,"
            "          row_number() OVER (PARTITION BY group_id ORDER BY attempt DESC) AS rn"
            "   FROM {analysis}.classification_run_items WHERE run_id = ?) WHERE rn = 1)")
        with db.connect(**self.ctx.db_config) as conn:
            st = conn.execute(self.sql(
                latest +
                " SELECT count(*) FILTER (WHERE status = 'loaded'),"
                "        count(*) FILTER (WHERE status = 'error')"
                " FROM latest"), (self.run_id,)).fetchone()
            kinds = conn.execute(self.sql(
                latest +
                " SELECT error_kind, count(*) FROM latest WHERE status = 'error'"
                " GROUP BY 1 ORDER BY 1"), (self.run_id,)).fetchall()
            tok = conn.execute(self.sql(
                "SELECT coalesce(sum(prompt_tokens), 0), coalesce(sum(cached_tokens), 0),"
                "       coalesce(sum(completion_tokens), 0), coalesce(sum(cost), 0)"
                " FROM {analysis}.classification_run_items WHERE run_id = ?"),
                (self.run_id,)).fetchone()
        assert st is not None and tok is not None
        n_loaded, n_err = st
        now = time.monotonic()
        rate_block = n_block / (now - t_block) if now > t_block else 0.0
        rate_run = self._n_sent / (now - t_session) if now > t_session else 0.0
        remaining = self.total - n_loaded - n_err
        eta = "-"
        if rate_run > 0:
            secs = int(remaining / rate_run)
            eta = f"{secs // 3600}h{secs % 3600 // 60:02d}m"
        by_kind = ", ".join(f"{k} {n}" for k, n in kinds) or "none"
        self.log(
            f"CHUNK {chunk_no} committed: {loaded} loaded, {members:,} member rows replaced\n"
            f"done {n_loaded + n_err:,}/{self.total:,}"
            f" ({(n_loaded + n_err) / self.total:.1%})  loaded {n_loaded:,}  errors {n_err:,}"
            f"  rate {rate_block:.2f}/s (chunk) {rate_run:.2f}/s (session)  ETA {eta}\n"
            f"tokens in {tok[0]:,} (cached {tok[1]:,}) out {tok[2]:,}  cost ${tok[3]:.4f} (run)"
            f" — errors by kind: {by_kind}")

    # ------------------------------------------------------------ the run

    def execute(self, retry_errors):
        groups = self.eligible_groups()
        self.total = len(groups)
        latest = self.latest_items()
        n_loaded = sum(1 for _, s in latest.values() if s == "loaded")
        n_err = sum(1 for _, s in latest.values() if s == "error")
        n_recv = sum(1 for _, s in latest.values() if s == "received")
        to_send = []
        for gid, cid, text in groups:
            prev = latest.get(gid)
            if prev is None:
                to_send.append((gid, cid, text, 1))
            elif retry_errors and prev[1] == "error":
                to_send.append((gid, cid, text, prev[0] + 1))
        self.done_before = n_loaded + (0 if retry_errors else n_err)
        n_unsent = len(to_send)
        if self.limit:
            to_send = to_send[:self.limit]
        p = self.profile
        self.log(
            f"RUN {self.run_id} started {self.run_ts:%Y-%m-%d %H:%M:%S}\n"
            f"prompt {p.prompt_name} v{p.version} (id {p.prompt_id}), {len(p.topics)} topics\n"
            f"model {self.model} (stamped {self.model_stamp}) via {self.client.base_url}\n"
            f"concurrency {self.concurrency}, chunk {self.chunk_size}\n"
            f"eligible groups {self.total:,} (canonical >= {MIN_COMMENT_LENGTH} chars):"
            f" loaded {n_loaded:,}, errors {n_err:,}, stored not loaded {n_recv:,},"
            f" to send now {len(to_send):,}"
            + (f" of {n_unsent:,} (--limit {self.limit})" if self.limit else "")
            + (" (incl. error retries)" if retry_errors else ""))

        t_session = time.monotonic()
        chunk_no = 0
        if n_recv:
            loaded, members = self.load_received()
            chunk_no += 1
            self.progress(chunk_no, loaded, members, t_session, 0, t_session)

        aborted = None
        pending = iter(to_send)
        in_flight = set()
        since_load = 0
        t_block = time.monotonic()
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            while True:
                while not self.stopping and aborted is None and len(in_flight) < self.concurrency:
                    nxt = next(pending, None)
                    if nxt is None:
                        break
                    in_flight.add(pool.submit(self.call, *nxt))
                if not in_flight:
                    break
                done, in_flight = wait(in_flight, return_when=FIRST_COMPLETED)
                for f in done:
                    exc = f.exception()
                    if exc is None:
                        try:
                            self.store(*f.result())
                        except Exception as store_exc:
                            exc = store_exc
                    if isinstance(exc, Abort):
                        if aborted is None:
                            aborted = exc
                            self.log(f"ABORT: {exc}\nfinishing {len(in_flight)} in flight")
                        continue
                    if exc is not None:
                        # A failure storing a call (the database): stop, keep what is stored.
                        if aborted is None:
                            aborted = exc
                            self.log(f"ABORT: {type(exc).__name__}: {exc}\n"
                                     f"finishing {len(in_flight)} in flight")
                        continue
                    since_load += 1
                if since_load >= self.chunk_size:
                    loaded, members = self.load_received()
                    chunk_no += 1
                    self.progress(chunk_no, loaded, members, t_block, since_load, t_session)
                    since_load = 0
                    t_block = time.monotonic()

        if since_load:
            loaded, members = self.load_received()
            chunk_no += 1
            self.progress(chunk_no, loaded, members, t_block, since_load, t_session)
        self.close()

        latest = self.latest_items()
        n_loaded = sum(1 for _, s in latest.values() if s == "loaded")
        n_err = sum(1 for _, s in latest.values() if s == "error")
        unsent = self.total - len(latest)
        how = "ABORTED" if aborted else ("STOPPED" if self.stopping else "FINISHED")
        self.log(f"RUN {self.run_id} {how}: loaded {n_loaded:,}, errors {n_err:,},"
                 f" not yet sent {unsent:,} of {self.total:,}")
        slug = self.ctx.slug
        if unsent:
            self.log(f"resume: python scripts/reclassify_groups.py --project {slug}"
                     f" --resume {self.run_id}")
        if n_err:
            self.log(f"retry the errors: python scripts/reclassify_groups.py --project {slug}"
                     f" --resume {self.run_id} --retry-errors")
        return 1 if aborted else 0


def _start_run(ctx, profile):
    """Record the run header and return (run_id, run_ts)."""
    run_ts = datetime.now()
    run_id = f"reclass_{run_ts:%Y%m%d_%H%M%S}"
    with db.connect(**ctx.db_config) as conn:
        n = conn.execute(ctx.render_sql(
            "SELECT count(*) FROM {analysis}.comment_group g"
            " JOIN {analysis}.v_source_comments c ON c.comment_id = g.canonical_comment_id"
            " WHERE length(c.comment_text) >= ?"), (MIN_COMMENT_LENGTH,)).fetchone()
        assert n is not None
        conn.execute(ctx.render_sql(
            "INSERT INTO {analysis}.classification_runs"
            " (run_timestamp, prompt_id, model_name, comment_count) VALUES (?, ?, ?, ?)"),
            (run_ts.isoformat(sep=" "), profile.prompt_id, model_of(configured_model()), n[0]))
    return run_id, run_ts


def list_runs(ctx, out=None):
    """Every run of classification_runs, newest last: its id, model, prompt,
    what it loaded, errored, stored unloaded, and has not sent of the eligible
    groups of today's partition; then the command that continues the latest run
    with groups left, or says there is none."""
    out = out or sys.stdout
    with db.connect(**ctx.db_config) as conn:
        total = conn.execute(ctx.render_sql(
            "SELECT count(*) FROM {analysis}.comment_group g"
            " JOIN {analysis}.v_source_comments c ON c.comment_id = g.canonical_comment_id"
            " WHERE length(c.comment_text) >= ?"), (MIN_COMMENT_LENGTH,)).fetchone()[0]
        rebuilt_at = conn.execute(ctx.render_sql(
            "SELECT max(built_at) FROM {analysis}.comment_group")).fetchone()[0]
        runs = conn.execute(ctx.render_sql(
            "SELECT run_timestamp, model_name, prompt_id, comment_count, created_at"
            " FROM {analysis}.classification_runs ORDER BY run_timestamp")).fetchall()
        rows = []
        for ts, model, prompt_id, n_groups, created in runs:
            run_id = f"reclass_{datetime.fromisoformat(ts):%Y%m%d_%H%M%S}"
            counts = dict(conn.execute(ctx.render_sql(
                "SELECT status, count(*) FROM ("
                "  SELECT status, row_number() OVER (PARTITION BY group_id ORDER BY attempt DESC) AS rn"
                "  FROM {analysis}.classification_run_items WHERE run_id = ?)"
                " WHERE rn = 1 GROUP BY status"), (run_id,)).fetchall())
            items = sum(counts.values())
            rows.append((run_id, model, prompt_id, n_groups, created, counts, items,
                         rebuilt_at is not None and created is not None and rebuilt_at > created))
    print(f"eligible groups today: {total:,} (canonical >= {MIN_COMMENT_LENGTH} chars)", file=out)
    if not rows:
        print("no stance run yet: make stance LIMIT=200 starts one", file=out)
        return
    continuable = None
    for run_id, model, prompt_id, n_groups, created, counts, items, rebuilt in rows:
        unsent = max(0, total - items)
        state = ("partition rebuilt since; cannot be continued" if rebuilt
                 else "complete" if unsent == 0 and not counts.get("error") and not counts.get("received")
                 else f"{unsent:,} not yet sent")
        print(f"{run_id}  model {model}  prompt id {prompt_id}  started {created}:"
              f" loaded {counts.get('loaded', 0):,}, errors {counts.get('error', 0):,},"
              f" stored not loaded {counts.get('received', 0):,}; {state}", file=out)
        if not rebuilt and (unsent or counts.get("received") or counts.get("error")):
            continuable = (run_id, unsent, counts.get("error", 0))
    slug = ctx.slug
    if continuable is None:
        print("nothing to continue: make stance LIMIT=200 starts a new run", file=out)
        return
    run_id, unsent, n_err = continuable
    print(f"to continue {run_id}: make stance RUN={run_id} (LIMIT=N for the next N groups,"
          f" CONCURRENCY=N for calls in flight)", file=out)
    print(f"  the same as: python scripts/reclassify_groups.py --project {slug} --resume {run_id}", file=out)
    if n_err:
        print(f"  with its {n_err:,} errors sent again: python scripts/reclassify_groups.py"
              f" --project {slug} --resume {run_id} --retry-errors", file=out)


def _resume_run(ctx, profile, run_id):
    """The run header of `run_id`; refuses a changed prompt or a rebuilt partition."""
    try:
        ts = datetime.strptime(run_id, "reclass_%Y%m%d_%H%M%S")
    except ValueError:
        raise SystemExit(f"{run_id!r} is not a run id (reclass_YYYYMMDD_HHMMSS)") from None
    with db.connect(**ctx.db_config) as conn:
        row = conn.execute(ctx.render_sql(
            "SELECT run_timestamp, prompt_id, created_at,"
            "       (SELECT max(built_at) FROM {analysis}.comment_group) > created_at"
            " FROM {analysis}.classification_runs"
            " WHERE strftime('%Y%m%d_%H%M%S', run_timestamp) = ?"),
            (f"{ts:%Y%m%d_%H%M%S}",)).fetchone()
    if row is None:
        raise SystemExit(f"No classification_runs row for {run_id}.")
    run_ts, prompt_id, _created, rebuilt = row
    if prompt_id != profile.prompt_id:
        raise SystemExit(
            f"{run_id} ran prompt id {prompt_id}; the active prompt is {profile.prompt_id}."
            " A resume must use the run's prompt.")
    if rebuilt:
        raise SystemExit(
            f"comment_group was rebuilt after {run_id} started — its group ids no longer"
            " match the stored calls. Start a new run.")
    return run_id, datetime.fromisoformat(run_ts)


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--project", required=True, help="Project slug")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--new-run", action="store_true", help="Start a new run")
    mode.add_argument("--resume", metavar="RUN_ID", help="Continue a run")
    mode.add_argument("--runs", action="store_true",
                      help="List the runs so far and the command that continues the latest")
    ap.add_argument("--retry-errors", action="store_true",
                    help="With --resume: also send again the groups whose latest call errored")
    ap.add_argument("--concurrency", type=int, default=16,
                    help="Calls in flight (default 16)")
    ap.add_argument("--chunk-size", type=int, default=500,
                    help="Stored responses per load transaction (default 500)")
    ap.add_argument("--limit", type=int, metavar="N",
                    help="Send at most N groups this session, store and load them,"
                         " then exit (a pilot; --resume sends the rest)")
    args = ap.parse_args()
    if args.limit is not None and args.limit < 1:
        ap.error("--limit must be >= 1")
    if args.retry_errors and not args.resume:
        ap.error("--retry-errors needs --resume")
    if args.concurrency < 1 or args.chunk_size < 1:
        ap.error("--concurrency and --chunk-size must be >= 1")

    ctx = ProjectContext.load(args.project)
    if args.runs:
        list_runs(ctx)
        return
    profile = ProjectProfile.load(ctx, "sentiment_topic")
    if args.new_run:
        run_id, run_ts = _start_run(ctx, profile)
    else:
        run_id, run_ts = _resume_run(ctx, profile, args.resume)

    log = RunLog(_REPO_ROOT / "logs" / f"reclassify_{run_id}.log")
    run = Run(ctx, profile, run_id, run_ts, args.concurrency, args.chunk_size, log,
              limit=args.limit)

    def _stop(_sig, _frame):
        run.stopping = True
        log("STOP requested: no new calls; finishing those in flight, loading, exiting."
            " Ctrl-C again to exit without loading (stored responses load on --resume).")
        signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGINT, _stop)

    try:
        code = run.execute(args.retry_errors)
    except Exception as exc:
        import traceback
        log(f"FAILED: {type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            f"Nothing of the failed load was committed; stored responses stay stored."
            f" Fix the cause, then --resume {run_id}.")
        raise SystemExit(1) from None
    sys.exit(code)


if __name__ == "__main__":
    main()
