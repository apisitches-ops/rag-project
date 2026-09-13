# Local RAG for Thai/English PDF Reports

A retrieval-augmented generation (RAG) system that answers questions about long PDF
reports — built and validated against a 233-page Thai-language corporate annual
report — with **every model running locally via [Ollama](https://ollama.com)**. No
API keys, no cloud calls, no data leaving the machine.

Ask a question in Thai or English, get an answer in the same language, grounded in the
source document, with a page-level citation for every claim — or an honest "I don't
know" instead of a guess when the document doesn't cover it.

```
$ PYTHONPATH=src ./venv/bin/python -m rag.query "ปตท. ตั้งเป้าหมาย Net Zero ภายในปีใด"
ปตท. ตั้งเป้าหมาย Net Zero ภายในปี พ.ศ. 2593

Sources:
- 20260316-ptt-one-report-2024-th.pdf (p. 128)
```

## Why this exists

Most RAG tutorials stop at "call an embedding API, call a vector DB, call an LLM API."
This project was built to actually work — fully offline, on a real Thai financial
document — which surfaces a lot of problems a toy demo never hits: garbled text
extraction, an embedding model that quietly misranks financial-table facts, a
context window that silently truncates instead of erroring, and an LLM that
sometimes just ignores your language instruction. Each of those is a real bug this
project found, diagnosed, and fixed — see [Engineering notes](#engineering-notes-the-interesting-part)
below.

Accuracy was measured, not assumed: a 30-question test set (easy/medium/hard, spanning
simple facts, financial-table lookups, and adversarial made-up questions) went from
**77% → 93%** correct across three rounds of diagnosed, verified fixes. Every round is
logged in [`docs/improvement-log.md`](docs/improvement-log.md).

## How it works

**Ingestion** (`src/rag/ingest.py`) — run once per new document:

```
PDF → extract text per page (pypdf)
    → normalize Thai text (pythainlp re-segmentation, not a regex heuristic)
    → split into chunks (~500 chars, recursive character splitting)
    → embed each chunk (bge-m3, batched to avoid overloading Ollama)
    → store (vector + text + source filename + page number) in Chroma
```

Re-running ingestion only processes files not already in the store, so adding a new
PDF to `data/raw/` doesn't re-embed everything.

**Query** (`src/rag/query.py`) — every time a question comes in:

```
question → embed with bge-m3
         → hybrid retrieval:
             (a) embedding similarity search (top 10)
             (b) + exact keyword-phrase fallback for terms the embedding
                 model ranks surprisingly low (see engineering notes)
         → threshold gate: does anything clear a relevance score of 0.3?
             no  → return "no relevant information found" (LLM never called)
             yes → prompt llama3.1:8b with only those chunks, instructed to:
                     - answer only from the given chunks, in the question's language
                     - verify a chunk names the exact thing asked, not just
                       something related
                     - report which chunks it actually used
         → answer + citations (filename + page) for the chunks actually used
```

## Getting started

**Prerequisites:** [Ollama](https://ollama.com) installed and running, Python 3.11+.

```bash
# 1. Set up the environment
python3.11 -m venv venv
./venv/bin/pip install -r requirements.txt

# 2. Pull the models (local, one-time download)
ollama pull bge-m3
ollama pull llama3.1:8b

# 3. Drop PDF(s) into data/raw/, then ingest
PYTHONPATH=src ./venv/bin/python -m rag.ingest

# 4. Ask questions
PYTHONPATH=src ./venv/bin/python -m rag.query "your question here"

# ...or start an interactive session (no argument)
PYTHONPATH=src ./venv/bin/python -m rag.query
```

`data/raw/` and the vector store (`data/processed/chroma/`) are gitignored — this repo
ships the pipeline, not the documents or the index. Bring your own PDFs.

## Evaluation

```bash
./venv/bin/pytest -q                    # unit tests (pure logic, no Ollama needed, <1s)
PYTHONPATH=src ./venv/bin/python scripts/eval30.py   # 30-question correctness suite (~15 min, hits Ollama)
```

| | Score |
|---|---|
| Baseline | 23/30 (77%) |
| After hybrid retrieval + prompt fixes | 27/30 (90%) |
| After fixing a silent context-window truncation bug | **28/30 (93%)** |

Full breakdown, root-cause diagnoses, and what's still known-broken:
[`docs/eval-set-30-stress-test.md`](docs/eval-set-30-stress-test.md) and
[`docs/improvement-log.md`](docs/improvement-log.md).

## Engineering notes (the interesting part)

A few real problems found and fixed along the way, not just "it works":

- **Thai PDF text extraction is subtly corrupted.** `pypdf` inserts spurious spaces
  mid-word due to PDF kerning artifacts — but Thai also legitimately uses single
  spaces between phrases, so a plain regex can't tell them apart (verified: a naive
  "delete all spaces between Thai characters" rule fixed the artifacts but also glued
  an entire table of contents into one unreadable run). The fix uses `pythainlp`'s
  dictionary-based tokenizer to re-segment the text properly instead of guessing from
  whitespace patterns.
- **The embedding model ranks some exact-term matches surprisingly low.** A financial
  chunk containing the literal, correctly-labeled figure for "total assets" ranked
  **22nd out of 30** candidates for a query asking exactly that — the model favored a
  textually-similar but different line ("total *current* assets") instead. A BGE-style
  query-instruction prefix was tested and made it *worse*. The fix: a keyword-phrase
  fallback that catches literal rare-term matches the embedding misses, gated by
  specificity (a phrase matching too many chunks, like "...Exchange of Thailand," is
  treated as too generic to trust and skipped — this was added *after* it caused a
  real regression on a previously-correct question).
- **Ollama silently truncates instead of erroring on context overflow.** Retrieval
  could assemble more chunks than the default context window fits; the fix (explicit
  `num_ctx`) turned a persistently-wrong answer into a correct one — proof the earlier
  "flakiness" wasn't just LLM randomness, part of it was silently dropped context.
- **A citation-parsing regex went through five iterations** to correctly handle real
  model output: markdown emphasis around the marker, trailing remarks after it,
  indentation, and prose that coincidentally starts with the same word as the marker —
  each fixing a concretely reproduced failure, not a hypothetical one.

## Project structure

```
src/rag/
  text_processing.py   pure functions: normalize_text, chunk_text, select_chunks
                        (no I/O — unit tested directly, no Ollama required)
  ingest.py             PDF → chunks → embeddings → Chroma
  query.py              question → retrieval → threshold gate → generation → citations
tests/                  unit tests for the pure logic layer
scripts/eval30.py        30-question correctness benchmark
docs/
  eval-set.md                    5-question hand-curated eval set
  eval-set-30-stress-test.md     30-question test, first-pass results + root causes
  improvement-log.md             round-by-round fix log with scores
CONTEXT.md              project glossary (Document, Chunk, Query, Citation, ...)
.scratch/rag-pdf-ollama/ original spec + tickets this was built from
```

## Known limitations

- Financial tables aren't chunked table-aware — plain recursive character splitting,
  patched with the keyword-phrase fallback above rather than restructured.
- The model occasionally still misreads the wrong column/year out of a multi-value
  table row (documented in `docs/improvement-log.md`); a known mitigation
  (self-consistency / majority-vote across repeated calls) hasn't been implemented.
- CLI only — no web UI or API server.
- PDF only, no OCR for scanned/image-only pages.
- Each question is answered independently — no multi-turn conversation memory.

## Tech stack

Python 3.11 · [LangChain](https://python.langchain.com/) (`langchain-ollama`,
`langchain-chroma`, `langchain-text-splitters`) · [ChromaDB](https://www.trychroma.com/)
· [Ollama](https://ollama.com) running `bge-m3` (embeddings) and `llama3.1:8b`
(generation) · [pythainlp](https://pythainlp.github.io/) · `pypdf` · `pytest`
