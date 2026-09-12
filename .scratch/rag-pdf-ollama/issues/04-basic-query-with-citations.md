# 04: Basic query with citations

**What to build:** A one-shot command-line query: give it a question, and it embeds the question, retrieves the most relevant Chunks from the vector store, and gets a local Generation Model to answer using them — replying in whichever language (Thai or English) the question was asked in — with a Citation (source filename + page number) shown for each Chunk actually used.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] The query entry point accepts a question as a command-line argument and returns a single answer
- [ ] The question is embedded with the same Embedding Model (`bge-m3`) used during ingestion
- [ ] The top-k most similar Chunks are retrieved from the vector store
- [ ] The Generation Model (`llama3.1:8b`) is prompted to answer using only the retrieved Chunks' text
- [ ] Asking a question in Thai returns an answer in Thai; asking the equivalent question in English returns an answer in English
- [ ] The answer is displayed together with a Citation (source filename + page number) for each Chunk that was actually used to produce it
- [ ] Asking a factual question answerable from the ingested PTT report returns a correct, cited answer
