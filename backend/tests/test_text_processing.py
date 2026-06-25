from app.text_processing import chunk_text, detect_language, detect_question_language, normalize_text


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


def test_chunk_text_uses_size_and_overlap() -> None:
    text = " ".join(f"word{i}" for i in range(12))
    chunks = chunk_text(text, chunk_size_tokens=5, chunk_overlap_tokens=2)
    assert [chunk.token_count for chunk in chunks] == [5, 5, 5, 3]
    assert chunks[0].text.split()[-2:] == chunks[1].text.split()[:2]
