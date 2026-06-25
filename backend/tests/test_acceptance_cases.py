from app.text_processing import detect_question_language


def answer_language_for_question(question: str) -> str:
    return detect_question_language(question)


def test_required_language_direction_cases() -> None:
    cases = [
        ("si_doc", "මෙහි ප්‍රධාන කරුණ කුමක්ද?", "si"),
        ("en_doc", "What does Earth support?", "en"),
        ("si_doc", "What does school education develop?", "en"),
        ("en_doc", "Earth ගැන කියන්නේ කුමක්ද?", "si"),
        ("mixed_doc", "තේ කර්මාන්තය වැදගත් ඇයි?", "si"),
        ("mixed_doc", "Where is tea cultivation common?", "en"),
    ]
    for _document, question, expected_language in cases:
        assert answer_language_for_question(question) == expected_language
