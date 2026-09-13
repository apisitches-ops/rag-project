import re
import sys

from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from pythainlp.tokenize import word_tokenize

from rag.ingest import get_vector_store
from rag.retry import with_retry
from rag.text_processing import Chunk, select_chunks

GENERATION_MODEL = "llama3.1:8b"
TOP_K = 10
SIMILARITY_THRESHOLD = 0.3
MAX_KEYWORD_PHRASES = 5
KEYWORD_MATCHES_PER_PHRASE = 5
# Embedding search (up to TOP_K) plus keyword-phrase fallback (up to
# MAX_KEYWORD_PHRASES * KEYWORD_MATCHES_PER_PHRASE more) can assemble a large
# prompt; Ollama's context-window default (2048-4096 depending on version) is
# too small for that and silently truncates rather than erroring, so it's set
# explicitly here with headroom.
GENERATION_NUM_CTX = 16384

_THAI_CHAR_PATTERN = re.compile(r"[ก-๙]")

PROMPT_TEMPLATE = """Answer the question using ONLY the numbered chunks below. Several chunks \
may look topically related without actually answering the specific question - before using a \
chunk, check that it names the exact entity/line-item the question asks about (e.g. "total \
assets" is not the same line as "total current assets"; one shareholder or subsidiary is not \
the same as another), and prefer the chunk that matches most precisely over one that is merely \
related. You MUST write your entire answer in {language}, regardless of what language the \
chunks themselves are written in - if a chunk is already in {language}, you may quote it \
directly; if it's in a different language, translate the facts you use into {language} rather \
than quoting the original wording. If the chunks don't contain the answer, say so in {language} \
instead of guessing.

{chunks}

Question: {question}

Reminder: write your answer in {language}, not any other language.

On the final line of your reply, output exactly "Used: " followed by a comma-separated list \
of the chunk numbers you actually drew on to answer (e.g. "Used: 1, 3"), or "Used: none" if \
you couldn't answer from the chunks."""

_USED_LINE = re.compile(
    r"^\s*[*_]*\s*used:\s*(none|\d+(?:\s*,\s*\d+)*)\s*[*_]*[.!]?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _keyword_phrases(question: str) -> list[str]:
    """2- and 3-token contiguous phrases from the question, longest first.

    Exact Thai financial terms (e.g. "สินทรัพย์ รวม") are often two tokens
    that embedding similarity alone can rank surprisingly low - literal
    substring matching on the phrase catches them regardless of embedding
    rank. Not filtered by stopwords: a word like "รวม" ("total") is generic
    alone but load-bearing as part of a compound term.
    """
    # Window over the ORIGINAL token sequence (not a pre-filtered one), so a
    # phrase is only formed from tokens genuinely adjacent in the question -
    # filtering non-Thai tokens out first would let e.g. "ปี" and "ของ"
    # (with a number and whitespace token between them) look adjacent and
    # get joined into a phantom, never-actually-adjacent "phrase".
    tokens = word_tokenize(question, engine="newmm")
    phrases = set()
    for n in (3, 2):
        for i in range(len(tokens) - n + 1):
            window = tokens[i : i + n]
            if all(_THAI_CHAR_PATTERN.search(t) for t in window):
                phrases.add(" ".join(window))
    return sorted(phrases, key=len, reverse=True)[:MAX_KEYWORD_PHRASES]


def _keyword_matches(vector_store: Chroma, question: str) -> list[Chunk]:
    chunks = []
    seen_ids = set()
    for phrase in _keyword_phrases(question):
        result = vector_store.get(
            where_document={"$contains": phrase},
            limit=KEYWORD_MATCHES_PER_PHRASE + 1,
            include=["documents", "metadatas"],
        )
        if len(result["ids"]) > KEYWORD_MATCHES_PER_PHRASE:
            # A phrase common enough to hit more than the limit is too generic
            # to trust as an exact-match boost (e.g. "ตลาดหลักทรัพย์ แห่ง" -
            # part of "Stock Exchange of Thailand", named on ~17 pages of a
            # financial report) - skip it rather than flood the context.
            continue
        for doc_id, doc, meta in zip(result["ids"], result["documents"], result["metadatas"]):
            if doc_id in seen_ids:
                continue
            seen_ids.add(doc_id)
            chunks.append(Chunk(text=doc, source=meta["source"], page=meta["page"]))
    return chunks


def retrieve(vector_store: Chroma, question: str, k: int = TOP_K) -> list[tuple[Chunk, float]]:
    """Hybrid retrieval: embedding similarity search, plus a keyword-phrase
    fallback for exact-term matches the embedding ranks low (see
    _keyword_phrases). Keyword hits are scored at exactly the threshold, so
    they clear select_chunks's gate without outranking genuine embedding
    matches.
    """
    results = with_retry(vector_store.similarity_search_with_relevance_scores, question, k=k)
    scored = [
        (Chunk(text=doc.page_content, source=doc.metadata["source"], page=doc.metadata["page"]), score)
        for doc, score in results
    ]
    seen_texts = {chunk.text for chunk, _ in scored}
    for chunk in _keyword_matches(vector_store, question):
        if chunk.text not in seen_texts:
            scored.append((chunk, SIMILARITY_THRESHOLD))
            seen_texts.add(chunk.text)
    return scored


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


def _detect_language(question: str) -> str:
    return "Thai" if _THAI_CHAR_PATTERN.search(question) else "English"


def _no_match_response(question: str) -> str:
    if _detect_language(question) == "Thai":
        return "ไม่พบข้อมูลที่เกี่ยวข้องในเอกสารที่มีอยู่สำหรับคำถามนี้"
    return "No relevant information was found in the ingested documents for this question."


def answer_question(vector_store: Chroma, llm: ChatOllama, question: str) -> str:
    scored_chunks = retrieve(vector_store, question)
    chunks = select_chunks(scored_chunks, threshold=SIMILARITY_THRESHOLD)
    if chunks is None:
        return _no_match_response(question)

    language = _detect_language(question)
    prompt = PROMPT_TEMPLATE.format(chunks=_format_chunks(chunks), question=question, language=language)
    raw_answer = with_retry(llm.invoke, prompt).content

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
    llm = ChatOllama(model=GENERATION_MODEL, num_ctx=GENERATION_NUM_CTX)

    if question:
        print(answer_question(vector_store, llm, question))
    else:
        _run_interactive(vector_store, llm)


if __name__ == "__main__":
    main()
