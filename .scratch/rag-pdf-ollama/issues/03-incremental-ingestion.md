# 03: Incremental ingestion for multiple documents

**What to build:** Ingestion discovers every PDF in the raw-documents folder (not just one hardcoded file) and only processes Documents that aren't already represented in the vector store, so adding a new PDF and re-running ingestion doesn't re-embed everything that was already done.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Ingestion discovers all PDF files present in the raw-documents folder automatically, with no filename hardcoded
- [ ] Before processing a Document, ingestion checks whether it's already represented in the vector store (via stored metadata, not a separate manifest file) and skips it if so
- [ ] Adding a second PDF to the raw-documents folder and re-running ingestion processes only the new file
- [ ] Re-running ingestion with no new files added makes no new embedding calls and leaves the vector store unchanged
- [ ] The vector store ends up containing Chunks from both Documents, each still correctly tagged with its own source filename and page numbers
