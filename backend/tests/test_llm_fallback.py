import pytest

from app.llm import LLMService
from app.schemas import SourceOut


@pytest.mark.asyncio
async def test_fallback_answer_language_is_sinhala(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_generate(_: str) -> str:
        raise RuntimeError("ollama unavailable")

    service = LLMService()
    monkeypatch.setattr(service, "_ollama_generate", fail_generate)
    answer = await service.answer(
        question="ප්‍රශ්නය කුමක්ද?",
        question_language="si",
        sources=[
            SourceOut(
                chunk_id="c1",
                document_id=1,
                filename="english.txt",
                text="This is English context.",
                page_number=None,
                score=0.9,
            )
        ],
    )
    assert "දේශීය LLM" in answer


@pytest.mark.asyncio
async def test_fallback_answer_language_is_english(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_generate(_: str) -> str:
        raise RuntimeError("ollama unavailable")

    service = LLMService()
    monkeypatch.setattr(service, "_ollama_generate", fail_generate)
    answer = await service.answer(
        question="What is the topic?",
        question_language="en",
        sources=[
            SourceOut(
                chunk_id="c1",
                document_id=1,
                filename="sinhala.txt",
                text="මෙය සිංහල පෙළකි.",
                page_number=None,
                score=0.9,
            )
        ],
    )
    assert answer.startswith("The local LLM service is unavailable")
