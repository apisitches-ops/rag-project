# 02: Single-document ingestion (happy path)

**What to build:** Running ingestion against a single PDF Document takes it all the way from raw file to queryable Chunks: text extraction, normalization, chunking, embedding, and storage in a local, persistent vector store — end to end, for one file.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Ingestion extracts text per page from a PDF Document (starting with the PTT 2024 One Report already in the raw-documents folder) using a PDF text extraction library
- [ ] Extracted text is normalized and chunked using the pure functions from ticket 01
- [ ] Each Chunk is embedded using the `bge-m3` Embedding Model via Ollama
- [ ] Each Chunk's vector, text, source filename, and page number are written to a local, persistent Chroma collection
- [ ] Running ingestion once against the one PDF completes without error and leaves the vector store non-empty
- [ ] Inspecting the vector store afterward shows Chunks whose metadata correctly identifies the source filename and page number they came from
