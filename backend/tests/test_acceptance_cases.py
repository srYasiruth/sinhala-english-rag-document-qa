import pytest

from app.rag import build_query_variants, determine_answer_language, merge_retrieval_rows, source_from_retrieval_row
from app.schemas import SourceOut
from app.text_processing import determine_requested_answer_language


def source(language_mix: str, text: str = "Context text", chunk_id: str = "c1") -> SourceOut:
    return SourceOut(
        chunk_id=chunk_id,
        document_id=1,
        filename="document.txt",
        text=text,
        page_number=None,
        score=0.9,
        language_mix=language_mix,
    )


def test_required_document_context_language_cases() -> None:
    cases = [
        ("en_doc", "What does Earth support?", [source("en")], "en"),
        ("si_doc", "\u0db8\u0dd9\u0dc4\u0dd2 \u0db4\u0dca\u200d\u0dbb\u0db0\u0dcf\u0db1 \u0d9a\u0dbb\u0dd4\u0dab \u0d9a\u0dd4\u0db8\u0d9a\u0dca\u0daf?", [source("si")], "si"),
        ("en_doc", "Earth \u0d9c\u0dd0\u0db1 \u0d9a\u0dd2\u0dba\u0db1\u0dca\u0db1\u0dda \u0d9a\u0dd4\u0db8\u0d9a\u0dca\u0daf?", [source("en")], "en"),
        ("si_doc", "What does school education develop?", [source("si")], "si"),
    ]

    for _document, _question, sources, expected_language in cases:
        assert determine_answer_language(sources) == expected_language


def test_required_question_language_answer_cases() -> None:
    cases = [
        ("en_doc", "What does Earth support?", "en"),
        ("en_doc", "Earth ගැන කියන්නේ කුමක්ද?", "si"),
        ("si_doc", "මෙහි ප්‍රධාන කරුණ කුමක්ද?", "si"),
        ("si_doc", "What does school education develop?", "en"),
        ("si_doc", "What does school education develop? Answer in Sinhala", "si"),
        ("en_doc", "Earth ගැන කියන්නේ කුමක්ද? Answer in English", "en"),
    ]

    for _document, question, expected_language in cases:
        assert determine_requested_answer_language(question) == expected_language


def test_mixed_retrieval_uses_majority_language() -> None:
    assert determine_answer_language([source("si", chunk_id="c1"), source("si", chunk_id="c2"), source("en", chunk_id="c3")]) == "si"
    assert determine_answer_language([source("en", chunk_id="c1"), source("en", chunk_id="c2"), source("si", chunk_id="c3")]) == "en"


def test_tie_or_unclear_uses_highest_ranked_detectable_language() -> None:
    english_first = [
        source("mixed", "This source contains mostly English text.", "c1"),
        source("si", chunk_id="c2"),
    ]
    sinhala_first = [
        source("mixed", "\u0db8\u0dd9\u0db8 \u0db8\u0dd6\u0dbd\u0dcf\u0dc1\u0dca\u200d\u0dbb\u0dba \u0dc3\u0dd2\u0d82\u0dc4\u0dbd \u0db4\u0dcf\u0da8\u0dba\u0d9a\u0dd2.", "c1"),
        source("en", chunk_id="c2"),
    ]

    assert determine_answer_language(english_first) == "en"
    assert determine_answer_language(sinhala_first) == "si"


def test_unclear_sources_fall_back_to_english() -> None:
    assert determine_answer_language([source("unknown", "12345")]) == "en"


def test_source_from_retrieval_row_handles_missing_metadata() -> None:
    result = source_from_retrieval_row(
        {
            "chunk_id": "missing-metadata",
            "text": None,
            "metadata": None,
            "score": 0.75,
        },
        ["English", "missing"],
    )

    assert result.document_id is None
    assert result.filename == "unknown"
    assert result.page_number is None
    assert result.text == ""
    assert result.score == 0.75
    assert result.language_mix == "unknown"
    assert result.highlights == []


def test_source_from_retrieval_row_handles_missing_text_score_and_chunk_id() -> None:
    result = source_from_retrieval_row({"metadata": None}, ["English"])

    assert result.chunk_id == "unknown-chunk"
    assert result.text == ""
    assert result.score == 0.0
    assert result.highlights == []


def test_answer_language_uses_source_text_when_metadata_language_is_missing() -> None:
    sources = [
        source("unknown", "This source is written in English.", "c1"),
        source("unknown", "12345", "c2"),
    ]

    assert determine_answer_language(sources) == "en"


@pytest.mark.asyncio
async def test_cross_language_query_expansion_translates_to_target_language(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_translate_query(_self: object, _question: str, target_language: str) -> str:
        return "translated to English" if target_language == "en" else "සිංහලට පරිවර්තනය"

    monkeypatch.setattr("app.rag.LLMService.translate_query", fake_translate_query)

    variants, translated = await build_query_variants("සිංහල ප්‍රශ්නය", "si", ["en"])

    assert variants == ["සිංහල ප්‍රශ්නය", "translated to English"]
    assert translated == ["translated to English"]


@pytest.mark.asyncio
async def test_same_language_query_expansion_does_not_translate(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(_self: object, _question: str, _target_language: str) -> str:
        raise AssertionError("translation should not be called")

    monkeypatch.setattr("app.rag.LLMService.translate_query", fail_if_called)

    variants, translated = await build_query_variants("What is this?", "en", ["en"])

    assert variants == ["What is this?"]
    assert translated == []


@pytest.mark.asyncio
async def test_query_expansion_falls_back_when_translation_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_translate_query(_self: object, _question: str, _target_language: str) -> None:
        return None

    monkeypatch.setattr("app.rag.LLMService.translate_query", fake_translate_query)

    variants, translated = await build_query_variants("What is this?", "en", ["si"])

    assert variants == ["What is this?"]
    assert translated == []


def test_merge_retrieval_rows_deduplicates_and_keeps_highest_score() -> None:
    rows = [
        {"chunk_id": "c1", "score": 0.4, "text": "old"},
        {"chunk_id": "c2", "score": 0.7, "text": "second"},
        {"chunk_id": "c1", "score": 0.9, "text": "new"},
    ]

    merged = merge_retrieval_rows(rows, top_k=2)

    assert [row["chunk_id"] for row in merged] == ["c1", "c2"]
    assert merged[0]["text"] == "new"
