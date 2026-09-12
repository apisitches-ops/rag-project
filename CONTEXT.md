# RAG Project

A local, retrieval-augmented question-answering system over Thai/English PDF reports (starting with PTT's 2024 One Report), running entirely on local models via Ollama.

## Language

**Document**:
A source PDF file placed in `data/raw/` that the system ingests (e.g. an annual report).
_Avoid_: File, report (unless referring to the specific PTT One Report)

**Ingestion**:
The process of parsing a Document, normalizing its extracted text, splitting it into Chunks, embedding them, and storing them in the Vector Store.
_Avoid_: Indexing, processing

**Chunk**:
A segment of a Document's extracted text, tagged with its source Document and page number, and stored as one retrieval unit in the Vector Store.
_Avoid_: Segment, passage

**Vector Store**:
The local Chroma collection that persists Chunk embeddings and metadata for similarity search.
_Avoid_: Index, database (alone)

**Embedding Model**:
`bge-m3`, run via Ollama, that converts Chunk text and Queries into vectors for similarity search. Chosen over `nomic-embed-text` for multilingual (Thai) quality.

**Generation Model**:
`llama3.1:8b`, run via Ollama, that produces the final answer from a Query and its retrieved Chunks.

**Query**:
A user's question, submitted in Thai or English, answered in whichever language it was asked in.
_Avoid_: Question (use Query when referring to the system's input specifically)

**Citation**:
The Document filename and page number attached to an answer, pointing back to the Chunk(s) it was derived from.
_Avoid_: Source, reference

**Eval Set**:
A small, manually-curated set of question/expected-answer pairs drawn from a Document, used to manually check end-to-end retrieval and answer quality when tuning chunking or the similarity threshold.
_Avoid_: Test set (reserved for automated unit tests of normalization/chunking code)
