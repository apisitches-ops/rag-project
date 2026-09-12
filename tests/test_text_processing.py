from rag.text_processing import Chunk, normalize_text, chunk_text, select_chunks


def test_normalize_text_collapses_repeated_whitespace():
    assert normalize_text("hello    world\n\n\tfoo") == "hello world foo"


def test_normalize_text_removes_spurious_space_between_thai_characters():
    assert normalize_text("ผลการดำ เนินงาน") == "ผลการดำเนินงาน"


def test_normalize_text_resegments_thai_words_via_dictionary_tokenizer():
    # "ก ารวิเคราะห์" glues into "การวิเคราะห์", which a dictionary tokenizer
    # correctly re-splits into its real two words ("การ" + "วิเคราะห์") -
    # a single space can't tell a real boundary from a PDF artifact, so we
    # can't just delete it and expect the two halves to stay merged.
    assert normalize_text("ก ารวิเคราะห์") == "การ วิเคราะห์"


def test_normalize_text_preserves_legitimate_word_boundaries():
    assert normalize_text("บริษัท ปตท. จำกัด (มหาชน)") == "บริษัท ปตท. จำกัด (มหาชน)"


def test_normalize_text_strips_leading_and_trailing_whitespace():
    assert normalize_text("  hello world  ") == "hello world"


def test_chunk_text_tags_each_chunk_with_source_and_page():
    chunks = chunk_text("short text", source="report.pdf", page=3)
    assert chunks == [Chunk(text="short text", source="report.pdf", page=3)]


def test_chunk_text_splits_long_text_into_multiple_chunks():
    long_text = "A" * 1200
    chunks = chunk_text(long_text, source="report.pdf", page=1, chunk_size=500, chunk_overlap=50)
    assert len(chunks) > 1
    assert all(c.source == "report.pdf" and c.page == 1 for c in chunks)
    assert all(len(c.text) <= 500 for c in chunks)


def test_select_chunks_returns_chunks_meeting_threshold():
    a = Chunk(text="a", source="s", page=1)
    b = Chunk(text="b", source="s", page=2)
    result = select_chunks([(a, 0.9), (b, 0.2)], threshold=0.5)
    assert result == [a]


def test_select_chunks_includes_score_equal_to_threshold():
    a = Chunk(text="a", source="s", page=1)
    result = select_chunks([(a, 0.5)], threshold=0.5)
    assert result == [a]


def test_select_chunks_returns_none_when_nothing_meets_threshold():
    a = Chunk(text="a", source="s", page=1)
    result = select_chunks([(a, 0.1)], threshold=0.5)
    assert result is None
