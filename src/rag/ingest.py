import sys
from pathlib import Path

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from pypdf import PdfReader

from rag.text_processing import chunk_text, normalize_text

EMBEDDING_MODEL = "bge-m3"
PERSIST_DIRECTORY = "data/processed/chroma"
COLLECTION_NAME = "documents"
EMBED_BATCH_SIZE = 64


def get_vector_store() -> Chroma:
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=OllamaEmbeddings(model=EMBEDDING_MODEL),
        persist_directory=PERSIST_DIRECTORY,
    )


def ingest_pdf(pdf_path: Path, vector_store: Chroma) -> int:
    """Extract, normalize, chunk, embed, and store one PDF's pages. Returns the number of Chunks added."""
    reader = PdfReader(pdf_path)

    chunks = []
    for page_number, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text()
        if not raw_text or not raw_text.strip():
            continue
        normalized = normalize_text(raw_text)
        chunks.extend(chunk_text(normalized, source=pdf_path.name, page=page_number))

    if not chunks:
        return 0

    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start : start + EMBED_BATCH_SIZE]
        vector_store.add_texts(
            texts=[chunk.text for chunk in batch],
            metadatas=[{"source": chunk.source, "page": chunk.page} for chunk in batch],
        )
    return len(chunks)


def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/20260316-ptt-one-report-2024-th.pdf")
    vector_store = get_vector_store()
    count = ingest_pdf(pdf_path, vector_store)
    print(f"Ingested {count} chunks from {pdf_path.name}")


if __name__ == "__main__":
    main()
