# 01: Project foundation: dependencies + pure text-processing logic

**What to build:** The project's dependency list reflects a fully local, Ollama-only pipeline (no cloud SDK, no redundant embedding library), and the pure text-processing logic that later ingestion/query tickets will build on — text normalization, chunking, and threshold-based chunk selection — exists as small, dependency-free functions with unit test coverage.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `requirements.txt` no longer lists `openai` or `sentence-transformers`; it lists only what a local Ollama-backed pipeline needs (an Ollama client/integration, a text-splitting/orchestration library, a vector store client, a PDF text extraction library)
- [ ] A normalization function takes raw extracted PDF text and returns text with spurious mid-word spacing artifacts collapsed/removed
- [ ] A chunking function takes normalized text plus a source identifier and page number, and returns a list of Chunks (text + source + page), using recursive character splitting
- [ ] A chunk-selection function takes a list of (Chunk, similarity score) pairs and a threshold, and returns either the Chunks that clear the threshold or an explicit "nothing cleared the threshold" result
- [ ] All three functions are pure: no network calls, no file I/O, no calls to Ollama or the vector store
- [ ] Unit tests cover each function using fabricated input strings/scores — no real PDF, no real model, no real vector store involved
- [ ] Unit tests run and pass without Ollama running and without any model pulled
