from app.text_processing import (
    chunk_text,
    detect_language,
    detect_question_language,
    determine_requested_answer_language,
    normalize_text,
)


def test_normalize_text_preserves_sinhala() -> None:
    text = "සිංහල   පෙළ\r\n\r\n\r\nEnglish"
    assert normalize_text(text) == "සිංහල පෙළ\n\nEnglish"


def test_detect_language_sinhala_english_and_mixed() -> None:
    assert detect_language("මෙය සිංහල ප්‍රශ්නයකි") == "si"
    assert detect_language("This is an English question") == "en"
    assert detect_language("මෙය Sinhala and English mixed text") == "mixed"


def test_detect_question_language_prefers_sinhala_when_mixed() -> None:
    assert detect_question_language("Earth ගැන කියන්නේ කුමක්ද?") == "si"
    assert detect_question_language("What does Earth support?") == "en"


def test_determine_requested_answer_language_uses_explicit_request_first() -> None:
    assert determine_requested_answer_language("What is Earth?") == "en"
    assert determine_requested_answer_language("Earth ගැන කියන්නේ කුමක්ද?") == "si"
    assert determine_requested_answer_language("Earth ගැන කියන්නේ කුමක්ද? Answer in English") == "en"
    assert determine_requested_answer_language("Earth ගැන කියන්නේ කුමක්ද? English වලින් දෙන්න") == "en"
    assert determine_requested_answer_language("What is Earth? Answer in Sinhala") == "si"
    assert determine_requested_answer_language("What is Earth? සිංහලෙන් දෙන්න") == "si"
    assert determine_requested_answer_language("12345") == "en"


def test_chunk_text_uses_size_and_overlap() -> None:
    text = " ".join(f"word{i}" for i in range(12))
    chunks = chunk_text(text, chunk_size_tokens=5, chunk_overlap_tokens=2)
    assert [chunk.token_count for chunk in chunks] == [5, 5, 5, 3]
    assert chunks[0].text.split()[-2:] == chunks[1].text.split()[:2]


def test_normalize_text_removes_page_numbers_and_repeated_headers() -> None:
    text = "\n".join(
        [
            "Report Header",
            "1",
            "Useful Sinhala text",
            "",
            "Report Header",
            "2",
            "Useful English text",
            "",
            "Report Header",
            "3",
            "Final text",
        ]
    )

    normalized = normalize_text(text)

    assert "Report Header" not in normalized
    assert "\n1\n" not in normalized
    assert "Useful Sinhala text" in normalized


def test_chunk_text_keeps_short_paragraphs_together() -> None:
    text = "First paragraph has useful context.\n\nSecond paragraph stays readable."

    chunks = chunk_text(text, chunk_size_tokens=20, chunk_overlap_tokens=5)

    assert len(chunks) == 1
    assert "First paragraph" in chunks[0].text
    assert "Second paragraph" in chunks[0].text
