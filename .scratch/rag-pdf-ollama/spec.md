Status: ready-for-agent

# Local RAG over Thai/English PDF Reports (Ollama-only)

## Problem Statement

The user needs to ask questions — in Thai or English — against long PDF reports (starting with PTT's 2024 One Report, a 233-page Thai-language financial annual report) and get answers grounded in the document's actual content, with a way to verify where an answer came from. The data is sensitive/proprietary enough that nothing should leave the machine: no cloud APIs, no external network calls for embeddings or generation.

## Solution

A local, fully-Ollama-powered RAG pipeline with two entry points:

- An **ingestion** step that discovers PDFs in the raw-documents folder, extracts and normalizes their text, splits it into Chunks, embeds each Chunk with a local multilingual Embedding Model, and stores the vectors plus source/page metadata in a local Vector Store. Re-running ingestion only processes Documents not already stored (incremental), not a full rebuild.
- A **query** entry point that accepts a Query (Thai or English, one-shot argument or an interactive loop when no argument is given), embeds it with the same Embedding Model, retrieves the closest Chunks from the Vector Store, and — only if at least one retrieved Chunk clears a similarity threshold — asks a local Generation Model to answer using those Chunks, in the same language the Query was asked in, with a Citation (Document filename + page number) for each Chunk used. Below threshold, it reports that no relevant information was found instead of guessing.

## User Stories

1. As a user, I want to drop PDF files into the raw-documents folder, so that they become queryable without any manual conversion step.
2. As a user, I want to run ingestion once and have it discover every PDF in that folder automatically, so that I don't have to name files individually.
3. As a user, I want to add a new PDF later and re-run ingestion, so that only the new file gets processed and my existing Chunks aren't needlessly re-embedded.
4. As a user, I want Thai text extracted from the PDFs to have its spacing artifacts cleaned up before chunking, so that Chunks aren't full of garbled mid-word spaces.
5. As a user, I want each Chunk to remember which Document and page it came from, so that answers can be traced back to a specific page.
6. As a user, I want to ask a question in Thai and get an answer in Thai, so that I don't have to translate anything myself.
7. As a user, I want to ask a question in English and get an answer in English, so that the system is usable regardless of which language I'm more comfortable in that moment.
8. As a user, I want every answer to show which Document(s) and page number(s) it drew from, so that I can verify the claim against the source report.
9. As a user, I want to be told explicitly when the system can't find relevant information, rather than receiving a confident-sounding guess, so that I don't mistake a hallucination for a real financial figure.
10. As a user, I want to ask a single one-off question from the command line (`query <question>`), so that I can script or quickly check one thing.
11. As a user, I want to start an interactive session (`query` with no argument) and ask several questions in a row, so that I don't pay PDF/model startup cost per question during a research session.
12. As a user, I want the whole pipeline — embeddings and generation — to run through models already available in my local Ollama installation, so that no data or query ever leaves my machine.
13. As a developer, I want the text-normalization and chunking logic covered by fast unit tests that don't require Ollama or a real PDF, so that I can iterate on that logic with quick feedback.
14. As a developer, I want the chunk-selection/threshold logic covered by fast unit tests using fabricated similarity scores, so that I can verify the "no relevant information" fallback without needing real embeddings.
15. As a developer, I want a small hand-curated Eval Set of question/expected-answer pairs drawn from the PTT report, so that I can manually sanity-check end-to-end retrieval and answer quality whenever I tune chunk size, overlap, or the similarity threshold.
16. As a maintainer, I want `requirements.txt` to only list packages actually used by this local-only pipeline, so that a fresh `pip install` doesn't pull in a cloud SDK (`openai`) or a redundant embedding library (`sentence-transformers`) the project no longer needs.

## Implementation Decisions

- **Ingestion module**: a module responsible for (a) discovering PDF Documents in the raw-documents folder, (b) skipping Documents already represented in the Vector Store (tracked by filename, checked against Vector Store metadata — no separate manifest file), (c) extracting text per page via `pypdf`, (d) normalizing whitespace (collapsing/removing spurious mid-word spaces introduced by PDF text extraction), (e) splitting normalized text into Chunks via recursive character splitting, (f) embedding each Chunk via the Embedding Model, and (g) writing Chunks (vector + text + source filename + page number) into the Vector Store.
- **Query module**: a module responsible for (a) accepting a Query as a CLI argument (one-shot) or via a REPL loop (no argument given), (b) embedding the Query with the same Embedding Model used at ingestion time, (c) retrieving the top-k nearest Chunks from the Vector Store, (d) applying the threshold/selection logic to decide whether any retrieved Chunk is relevant enough, (e) if none clear the threshold, returning a "no relevant information found" response without calling the Generation Model, (f) otherwise, prompting the Generation Model with the Query and the selected Chunks' text, instructed to answer in the Query's language and to only use the supplied Chunks, and (g) presenting the answer together with a Citation (filename + page) per Chunk actually used.
- **Pure logic layer** (the seam — see Testing Decisions): text normalization, chunking, and threshold-based chunk selection are implemented as functions with no I/O, no Ollama calls, and no Vector Store access — they take plain data in and return plain data out.
- **Embedding Model**: `bge-m3` via Ollama (chosen over the already-pulled `nomic-embed-text` for multilingual/Thai retrieval quality). Needs to be pulled before first ingestion.
- **Generation Model**: `llama3.1:8b` via Ollama (already pulled; sized for the available 16GB RAM).
- **Vector Store**: a local, persistent Chroma collection. Each stored vector carries metadata: source filename and page number, sufficient to reconstruct a Citation and to support the incremental-ingestion skip check.
- **Language handling**: no explicit language-detection step is a hard requirement — the Generation Model is instructed (via prompt) to answer in the same language as the Query. Both Thai and English Queries must be supported.
- **No-match behavior**: a similarity threshold (exact numeric value to be tuned empirically against the Eval Set) is applied to retrieved Chunks; if none clear it, the system responds that no relevant information was found instead of invoking the Generation Model with weak/irrelevant context.
- **Dependency cleanup**: `openai` and `sentence-transformers` are removed from `requirements.txt`; the project depends only on Ollama-backed embedding/generation, `langchain` (for text splitting and orchestration), `chromadb`, and `pypdf`.
- **CLI shape**: a single query entry point supports both one-shot (question passed as an argument) and interactive-loop (no argument) modes — not two separate scripts.

## Testing Decisions

- A good test here exercises the **pure logic layer** only (normalization, chunking, threshold-based selection) through its inputs and outputs — never mocks Ollama or Chroma, and never asserts on internal intermediate representations.
- **Unit-tested modules**: the text-normalization function, the chunking function, and the chunk-selection/threshold function. These have no prior art in this repo (greenfield `tests/`); use plain input-in/output-out assertions (e.g. pytest) with fabricated strings and fabricated (Chunk, score) pairs — no real PDF or model call required.
- **Not unit-tested (manual only)**: PDF parsing against the real file, embedding calls, Vector Store reads/writes, and full ingest/query orchestration. These are checked via the Eval Set: a small (5-10 pair) hand-written set of Thai questions with expected answers/facts drawn from the PTT report, run manually against the live CLI whenever chunking, the embedding model, or the threshold changes.

## Out of Scope

- Table-aware or page-layout-aware PDF chunking (revisit only if plain recursive-character chunking proves inadequate against the Eval Set).
- Any web UI, HTTP API, or server process — CLI only.
- Automated end-to-end evaluation (the Eval Set is run and judged manually, not asserted in CI).
- Multi-user access, auth, or concurrent request handling.
- Any cloud LLM/embedding fallback or hybrid local/cloud mode.
- File formats other than PDF.
- Conversation memory / multi-turn follow-up questions (each Query is answered independently).
- Streaming token-by-token output.
- OCR for scanned/image-only pages.

## Further Notes

- Target machine: Apple M1 Pro, 16GB RAM — this is why `llama3.1:8b` (not a larger model) and a single 8b-class Generation Model were chosen.
- Ollama already has `llama3.1:8b` and `nomic-embed-text` pulled locally; `bge-m3` still needs to be pulled (`ollama pull bge-m3`) before ingestion can run.
- System Python is 3.9.6; recommend using the `venv` setup already documented in `README.md` rather than the system interpreter.
- The first real Document is `data/raw/20260316-ptt-one-report-2024-th.pdf` (233 pages); `pypdf` was confirmed able to extract its Thai text, with minor spacing artifacts that the normalization step is meant to address.
- Domain vocabulary (Document, Chunk, Ingestion, Vector Store, Embedding Model, Generation Model, Query, Citation, Eval Set) is defined in `CONTEXT.md` at the repo root — use these terms, not synonyms, in code, tests, and future tickets.
