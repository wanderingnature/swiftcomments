# The record documents: make docindex

`make docindex` loads the action's record documents into the file: the Draft EIS
volumes, the Biological Assessments, the Economic Analysis, the notices, the Tribal
Summary Impact Statement, and the orders the NOI cites. The step gives each document its
sections, its chunks, and one vector per chunk. A comment sentence and a document chunk
then compare by cosine, under the same embedding model.

## The input

The step reads markdown files from `deis/`, one per document. Each file is a conversion
of the source PDF. The conversion keeps the heading levels and marks every page with a
`<!-- page N -->` line. A file without page markers is refused. The file names and
titles are fixed in `scripts/docindex/ingest_documents.py` (`SOURCES`); a file in
`deis/` that `SOURCES` does not name stops the step.

## What the step does

1. It splits each document into sections by its heading tree. The agency-letters
   volume is split one section per letter instead.
2. It splits each section into 600-character chunks with 100 overlap. Table-of-contents
   sections are skipped.
3. It records, for every section and chunk, the character offsets into the source file
   and the pages it spans.
4. It embeds every chunk with the embedding server of `.env` (`EMBED_BASE_URL`,
   `EMBED_MODEL`). Page markers, image references and `<sup>`/`<sub>` tags are not
   sent; the stored text keeps them.

The step is resumable. A document already ingested with the same SHA-256 is skipped. A
changed document is refused unless `REPLACE=1`, which deletes its rows first. A chunk
with a vector for the model is not sent again.

## The commands

```
make docindex DRY=1     segment and chunk, print the counts, write nothing
make docindex           ingest and embed
make docindex REPLACE=1 SKIP=<file>
```

## The tables

| Table | One row per |
|---|---|
| `doc_documents` | source file, with its SHA-256 |
| `doc_sections` | section: heading path, kind (front, toc, body, letter), offsets, pages |
| `doc_chunks` | chunk: text, offsets, pages |
| `doc_chunk_embeddings` | chunk and model: the vector, packed as `sentence_embedding` packs one |
