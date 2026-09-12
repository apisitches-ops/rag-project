import re
import sys

from langchain_chroma import Chroma
from langchain_ollama import ChatOllama

from rag.ingest import get_vector_store
from rag.text_processing import Chunk, select_chunks

GENERATION_MODEL = "llama3.1:8b"
TOP_K = 5
SIMILARITY_THRESHOLD = 0.3

_THAI_CHAR_PATTERN = re.compile(r"[ก-๙]")

PROMPT_TEMPLATE = """Answer the question using ONLY the numbered chunks below. Reply in the \
same language the question was asked in (Thai or English). If the chunks don't contain \
the answer, say so instead of guessing.

{chunks}

Question: {question}

On the final line of your reply, output exactly "Used: " followed by a comma-separated list \
of the chunk numbers you actually drew on to answer (e.g. "Used: 1, 3"), or "Used: none" if \
you couldn't answer from the chunks."""

_USED_LINE = re.compile(
    r"^\s*[*_]*\s*used:\s*(none|\d+(?:\s*,\s*\d+)*)\s*[*_]*[.!]?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def retrieve(vector_store: Chroma, question: str, k: int = TOP_K) -> list[tuple[Chunk, float]]:
    results = vector_store.similarity_search_with_relevance_scores(question, k=k)
    return [
        (Chunk(text=doc.page_content, source=doc.metadata["source"], page=doc.metadata["page"]), score)
        for doc, score in results
    ]


def _format_chunks(chunks: list[Chunk]) -> str:
    return "\n\n".join(f"[{i}] (from {chunk.source}, page {chunk.page})\n{chunk.text}" for i, chunk in enumerate(chunks, start=1))


def _extract_used_line(answer: str) -> tuple[str, str | None]:
    """Pull out the 'Used: ...' marker line the model was asked to include.

    Matched anywhere a line starts with it (re.MULTILINE), not just when
    it's the literal last line - models often add trailing remarks after
    it. The captured value is constrained to "none" or a digit list, so a
    prose line that merely starts with "used:" (mid-sentence or not) can't
    be mistaken for the marker - only a line that also has the expected
    shape counts.
    """
    matches = list(_USED_LINE.finditer(answer))
    if not matches:
        return answer.strip(), None
    match = matches[-1]
    remaining = (answer[: match.start()] + answer[match.end() :]).strip()
    return remaining, match.group(1).strip()


def _parse_used_indices(used_value: str | None, chunk_count: int) -> set[int]:
    if used_value is None:
        # No marker line at all: the model didn't follow the format, so fall
        # back to citing everything retrieved rather than nothing.
        return set(range(1, chunk_count + 1))
    numbers = re.findall(r"\d+", used_value)
    return {int(n) for n in numbers if 1 <= int(n) <= chunk_count}


def _format_citations(chunks: list[Chunk], used_indices: set[int]) -> str:
    tags = []
    for i, chunk in enumerate(chunks, start=1):
        if i not in used_indices:
            continue
        tag = f"{chunk.source} (p. {chunk.page})"
        if tag not in tags:
            tags.append(tag)
    return "\n".join(f"- {tag}" for tag in tags)


def _no_match_response(question: str) -> str:
    if _THAI_CHAR_PATTERN.search(question):
        return "ไม่พบข้อมูลที่เกี่ยวข้องในเอกสารที่มีอยู่สำหรับคำถามนี้"
    return "No relevant information was found in the ingested documents for this question."


def answer_question(vector_store: Chroma, llm: ChatOllama, question: str) -> str:
    scored_chunks = retrieve(vector_store, question)
    chunks = select_chunks(scored_chunks, threshold=SIMILARITY_THRESHOLD)
    if chunks is None:
        return _no_match_response(question)

    prompt = PROMPT_TEMPLATE.format(chunks=_format_chunks(chunks), question=question)
    raw_answer = llm.invoke(prompt).content

    answer, used_value = _extract_used_line(raw_answer)
    used_indices = _parse_used_indices(used_value, len(chunks))
    citations = _format_citations(chunks, used_indices)

    return f"{answer}\n\nSources:\n{citations}" if citations else answer


def _run_interactive(vector_store: Chroma, llm: ChatOllama) -> None:
    print("Interactive mode. Type a question, or 'exit'/'quit' to leave.")
    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            break
        try:
            print(answer_question(vector_store, llm, question))
        except Exception as e:
            print(f"Error answering that question: {e}")
        print()


def main() -> None:
    question = " ".join(sys.argv[1:])
    vector_store = get_vector_store()
    llm = ChatOllama(model=GENERATION_MODEL)

    if question:
        print(answer_question(vector_store, llm, question))
    else:
        _run_interactive(vector_store, llm)


if __name__ == "__main__":
    main()
