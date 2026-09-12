import re
import sys

from langchain_chroma import Chroma
from langchain_ollama import ChatOllama

from rag.ingest import get_vector_store
from rag.text_processing import Chunk

GENERATION_MODEL = "llama3.1:8b"
TOP_K = 5

PROMPT_TEMPLATE = """Answer the question using ONLY the numbered passages below. Reply in the \
same language the question was asked in (Thai or English). If the passages don't contain \
the answer, say so instead of guessing.

{passages}

Question: {question}

On the final line of your reply, output exactly "Used: " followed by a comma-separated list \
of the passage numbers you actually drew on to answer (e.g. "Used: 1, 3"), or "Used: none" if \
you couldn't answer from the passages."""

_USED_LINE = re.compile(r"used:\s*(.*)", re.IGNORECASE)


def retrieve(vector_store: Chroma, question: str, k: int = TOP_K) -> list[tuple[Chunk, float]]:
    results = vector_store.similarity_search_with_relevance_scores(question, k=k)
    return [
        (Chunk(text=doc.page_content, source=doc.metadata["source"], page=doc.metadata["page"]), score)
        for doc, score in results
    ]


def _format_passages(chunks: list[Chunk]) -> str:
    return "\n\n".join(f"[{i}] (from {chunk.source}, page {chunk.page})\n{chunk.text}" for i, chunk in enumerate(chunks, start=1))


def _parse_used_indices(answer: str, chunk_count: int) -> set[int]:
    match = _USED_LINE.search(answer)
    if not match:
        return set(range(1, chunk_count + 1))
    numbers = re.findall(r"\d+", match.group(1))
    used = {int(n) for n in numbers if 1 <= int(n) <= chunk_count}
    return used or set(range(1, chunk_count + 1))


def _format_citations(chunks: list[Chunk], used_indices: set[int]) -> str:
    tags = []
    for i, chunk in enumerate(chunks, start=1):
        if i not in used_indices:
            continue
        tag = f"{chunk.source} (p. {chunk.page})"
        if tag not in tags:
            tags.append(tag)
    return "\n".join(f"- {tag}" for tag in tags)


def answer_question(vector_store: Chroma, llm: ChatOllama, question: str) -> str:
    scored_chunks = retrieve(vector_store, question)
    chunks = [chunk for chunk, _ in scored_chunks]

    prompt = PROMPT_TEMPLATE.format(passages=_format_passages(chunks), question=question)
    raw_answer = llm.invoke(prompt).content

    used_indices = _parse_used_indices(raw_answer, len(chunks))
    answer = _USED_LINE.sub("", raw_answer).strip()
    citations = _format_citations(chunks, used_indices)

    return f"{answer}\n\nSources:\n{citations}" if citations else answer


def main() -> None:
    question = " ".join(sys.argv[1:])
    if not question:
        print("Usage: python -m rag.query <question>")
        return

    vector_store = get_vector_store()
    llm = ChatOllama(model=GENERATION_MODEL)
    print(answer_question(vector_store, llm, question))


if __name__ == "__main__":
    main()
