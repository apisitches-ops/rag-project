import re
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pythainlp.tokenize import word_tokenize
from pythainlp.util import normalize as thai_normalize

_WHITESPACE_RUN = re.compile(r"\s+")
_THAI_CHAR = r"[ก-ฺเ-๎]"
_THAI_RUN = re.compile(rf"{_THAI_CHAR}(?:[ ]?{_THAI_CHAR})*")


def normalize_text(text: str) -> str:
    """Fix PDF-extraction artifacts in Thai text.

    A single space between two Thai characters is ambiguous: it might be a
    real word/phrase boundary, or a spurious space PDF extraction inserted
    mid-word. Plain regex can't tell them apart, so within each run of Thai
    characters we strip all internal spaces and re-segment it with a
    dictionary-based Thai tokenizer, which finds real word boundaries
    independent of spacing.
    """
    text = thai_normalize(text)
    text = _WHITESPACE_RUN.sub(" ", text.strip())

    def resegment(match: re.Match[str]) -> str:
        return " ".join(word_tokenize(match.group(0).replace(" ", ""), engine="newmm"))

    return _THAI_RUN.sub(resegment, text)


@dataclass
class Chunk:
    text: str
    source: str
    page: int


def chunk_text(text: str, source: str, page: int, chunk_size: int = 500, chunk_overlap: int = 50) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return [Chunk(text=piece, source=source, page=page) for piece in splitter.split_text(text)]


def select_chunks(scored_chunks: list[tuple[Chunk, float]], threshold: float) -> list[Chunk] | None:
    """Return chunks whose similarity score clears the threshold, or None if none do."""
    selected = [chunk for chunk, score in scored_chunks if score >= threshold]
    return selected or None
