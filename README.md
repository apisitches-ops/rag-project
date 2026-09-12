# RAG Project

A retrieval-augmented generation project.

## Structure

- `data/raw/` — source documents (PDFs, text, etc.)
- `data/processed/` — cleaned/chunked data ready for embedding
- `src/` — ingestion, embedding, retrieval, and query code
- `tests/` — tests
- `notebooks/` — exploration notebooks
- `docs/` — notes and design docs

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
