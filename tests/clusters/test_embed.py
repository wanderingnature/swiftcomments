"""Step 11, the vectors (scripts/clusters/embed.py, shared/embeddings.py), in a
real temporary file: the input string and its hash for each view, the packed
vector, the queue of sentences with no vector for a model and an instruction,
the write, the server from .env and its stops, and a dry run. No request is
sent: the server is the reader's.

    uv run pytest tests/clusters
"""
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

from shared import db, embeddings  # noqa: E402
from clusters import embed  # noqa: E402


@pytest.fixture
def sentences_file(tmp_path, monkeypatch):
    path = tmp_path / "roadless.sqlite"
    conn = db.connect(path, create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.executemany("INSERT INTO gate_sentence VALUES (?, ?, 1, 1, 0, 0, 1, 0, 1, 0)",
                     [("k1", "Roads raise ignitions."), ("k2", "Table 21 shows it."), ("k3", "Bull trout need cold water.")])
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", path)
    return path


def test_input_string_and_hash():
    assert embed.wrap("", "text") == "text"
    assert embed.wrap("Do this", "text") == "Instruct: Do this\nQuery:text"
    assert embed.input_sha256("", "text") != embed.input_sha256(embed.VIEWS["topic"], "text")
    assert embed.VIEWS["comment"].startswith("Given a public comment on a federal rule")


def test_pack_and_unpack():
    v = np.arange(embeddings.DIMENSIONS, dtype=np.float32) / 7
    assert np.array_equal(embed.unpack(embed.pack(v)), v)
    with pytest.raises(ValueError, match="1024 were expected"):
        embed.pack([0.0, 1.0])


def test_queue_and_write(sentences_file):
    conn = db.connect(sentences_file)
    topic = embed.VIEWS["topic"]
    assert [k for k, _ in embed.queue(conn, "m", topic)] == ["k1", "k2", "k3"]
    vec = np.ones(embeddings.DIMENSIONS, dtype=np.float32)
    assert embed.write(conn, "m", topic, [("k2", "Table 21 shows it.")], [vec]) == 1
    # k2 has a vector for this model and instruction, and none for another.
    assert [k for k, _ in embed.queue(conn, "m", topic)] == ["k1", "k3"]
    assert [k for k, _ in embed.queue(conn, "m", "")] == ["k1", "k2", "k3"]
    row = conn.execute("SELECT * FROM sentence_embedding").fetchone()
    assert (row["dimensions"], row["input_sha256"]) == (1024, embed.input_sha256(topic, "Table 21 shows it."))
    assert np.array_equal(embed.unpack(row["vector"]), vec)
    conn.execute("DELETE FROM gate_sentence")
    with pytest.raises(SystemExit, match="run make sentences first"):
        embed.queue(conn, "m", topic)
    conn.close()


def test_server_from_env(monkeypatch):
    for name in ("EMBED_BASE_URL", "EMBED_API_KEY", "EMBED_MODEL"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(SystemExit, match="EMBED_BASE_URL and EMBED_MODEL not set"):
        embeddings.server()
    monkeypatch.setenv("EMBED_BASE_URL", "https://example.test/v1/embeddings/")
    monkeypatch.setenv("EMBED_MODEL", "qwen3-embedding-8b")
    assert embeddings.server() == ("https://example.test/v1", "", "qwen3-embedding-8b")


def test_dry_run_sends_nothing(sentences_file, monkeypatch, capsys):
    monkeypatch.setenv("EMBED_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("EMBED_MODEL", "m")
    assert embed.main(["--view", "plain", "--limit", "2", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "3 distinct sentences, 0 with a vector; 2 to send" in out and "nothing sent" in out
    conn = db.connect(sentences_file)
    assert conn.execute("SELECT count(*) FROM sentence_embedding").fetchone()[0] == 0
    conn.close()


def test_a_longer_vector_is_cut_to_its_leading_dimensions():
    full = np.arange(1, 4097, dtype=np.float64)
    cut = np.asarray(embeddings.leading(full))
    assert len(cut) == embeddings.DIMENSIONS
    assert np.isclose(np.linalg.norm(cut), 1.0)
    assert np.allclose(cut, full[:1024] / np.linalg.norm(full[:1024]))
    same = np.ones(embeddings.DIMENSIONS)
    assert embeddings.leading(same) == same.tolist()
    with pytest.raises(RuntimeError, match="768 values, fewer than 1024"):
        embeddings.leading(np.ones(768))


def test_concurrency_from_env(monkeypatch):
    monkeypatch.delenv("EMBED_CONCURRENCY", raising=False)
    assert embeddings.concurrency() == 8
    monkeypatch.setenv("EMBED_CONCURRENCY", "1")
    assert embeddings.concurrency() == 1
    monkeypatch.setenv("EMBED_CONCURRENCY", "0")
    with pytest.raises(SystemExit, match="1 or more"):
        embeddings.concurrency()
