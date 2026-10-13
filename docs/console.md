# The console

A read-only browser of `data/roadless.sqlite`, for checking on a run and looking at
what the steps wrote. It is not the analysis: the nine steps run from `make`, and the
console launches nothing. It opens the file with SQLite's `query_only` pragma, so
nothing typed into it can write, and it can be open while a step is writing (the file
is in write-ahead-log mode; readers do not block the writer or wait for it).

```
make console
```

prints a local URL (port 8501 unless taken); open it in a browser. The sidebar names
the file, its size, when it was last written, and the size of its write-ahead log,
which is non-zero while a step is writing or until SQLite folds the log back into the
file.

## The four pages

**Steps.** Every `make` target in run order, each with the rows it has written: the
corpus's records and files, the hashes, the n-grams and near-duplicate groups, the
named entities by type, the six entity tables by strict and loose mode, the floor's
survivors and its four detectors, the families and the group partition by kind, the
screen classes, the stance run's latest items by status (received, loaded, error)
with its tokens and seconds, the substance scores by how they were reached and by
band, the answerability levels, the attachment text by rendition, the file kinds, the
roster by sender and stance, the campaign organisations by basis. A step that has
written nothing says "not run". Reload the page for current counts; it caches
nothing.

**Comment.** One comment id (`FS-2025-0001-nnnnn`): its text, then every row the
steps hold about it, one table each: the attachment files, the hash row, the
near-duplicate group, the text family and the comment group, the active stance and
its topics, the entity scan state and the dictionary matches, the named entities, the
floor, the screen, the substance score and its parts, the answerability, the
attachment text and kind and count, the roster row, the campaign's organisation. A
table with no row for the comment says "no row".

**Tables.** Any table or view, a hundred rows at a time from any offset, with the
table's row count. Views are not counted, because two of them walk the whole file.

**Query.** SQL typed in, run read-only; the first 10,000 rows shown and downloadable
as CSV. A statement that would write is refused by SQLite with "attempt to write a
readonly database". The registered functions of `shared/db.py` (`regexp`,
`regexp_count`, `md5`, `authority_family_key`, `stddev`) are available.

## Where it lives

`console/queries.py` holds every query, with no Streamlit in it; `console/app.py` is
the pages. `tests/test_console.py` runs every query on the schema over a temporary
file and renders each page through Streamlit's test harness, the script run
in-process with the file path pointed at the temporary file. Streamlit is the
`console` dependency group of `pyproject.toml`, which the `dev` group includes, so
`uv sync` installs it and `uv run pytest` covers it.
