from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from app.llm import LLMService
from app.schemas import SourceOut


class FakeResponse:
    def __init__(self, payload: dict[str, Any]):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


class FakeAsyncClient:
    payloads: list[dict[str, Any]] = []
    response_payload: dict[str, Any] = {"response": "Generated answer"}
    exception: Exception | None = None
    timeout_value: int | None = None

    def __init__(self, timeout: int):
        self.timeout = timeout
        FakeAsyncClient.timeout_value = timeout

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, _: str, json: dict[str, Any]) -> FakeResponse:
        FakeAsyncClient.payloads.append(json)
        if FakeAsyncClient.exception:
            raise FakeAsyncClient.exception
        return FakeResponse(FakeAsyncClient.response_payload)


@pytest.fixture()
def service() -> LLMService:
    llm = LLMService()
    llm.settings = SimpleNamespace(
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen3:4b",
        ollama_timeout_seconds=300,
        ollama_keep_alive="10m",
        max_context_chars=160,
        max_source_chars=50,
    )
    return llm


def source(text: str, chunk_id: str = "c1") -> SourceOut:
    return SourceOut(
        chunk_id=chunk_id,
        document_id=1,
        filename="document.txt",
        text=text,
        page_number=None,
        score=0.9,
        language_mix="en",
    )


def test_context_trims_large_source_chunks(service: LLMService) -> None:
    context = service._build_context([source("A" * 200)])

    assert "A" * 50 in context
    assert "A" * 51 not in context


def test_context_caps_total_prompt_context(service: LLMService) -> None:
    context = service._build_context(
        [
            source("A" * 80, "c1"),
            source("B" * 80, "c2"),
            source("C" * 80, "c3"),
            source("D" * 80, "c4"),
        ]
    )

    assert len(context) <= service.settings.max_context_chars + 4
    assert "D" * 20 not in context


@pytest.mark.asyncio
async def test_ollama_payload_uses_configured_timeout_and_keep_alive(
    monkeypatch: pytest.MonkeyPatch,
    service: LLMService,
) -> None:
    FakeAsyncClient.payloads = []
    FakeAsyncClient.response_payload = {"response": "Generated answer"}
    FakeAsyncClient.exception = None
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    answer = await service.answer("What is this about?", "en", [source("This is English context.")])

    assert answer == "Generated answer"
    assert FakeAsyncClient.timeout_value == 300
    assert FakeAsyncClient.payloads[0]["keep_alive"] == "10m"


@pytest.mark.asyncio
async def test_prompt_uses_selected_user_answer_language(
    monkeypatch: pytest.MonkeyPatch,
    service: LLMService,
) -> None:
    FakeAsyncClient.payloads = []
    FakeAsyncClient.response_payload = {"response": "Generated answer"}
    FakeAsyncClient.exception = None
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    await service.answer(
        "Earth \u0d9c\u0dd0\u0db1 \u0d9a\u0dd2\u0dba\u0db1\u0dca\u0db1\u0dda \u0d9a\u0dd4\u0db8\u0d9a\u0dca\u0daf?",
        "en",
        [source("This is English context.")],
    )

    prompt = FakeAsyncClient.payloads[0]["prompt"]
    assert "Answer strictly in English." in prompt
    assert "selected from the user's question or explicit language request" in prompt
    assert "Use only the provided document context." in prompt
    assert "same language as the provided document context" not in prompt


@pytest.mark.asyncio
async def test_timeout_returns_sinhala_timeout_fallback(
    monkeypatch: pytest.MonkeyPatch,
    service: LLMService,
) -> None:
    FakeAsyncClient.payloads = []
    FakeAsyncClient.exception = httpx.TimeoutException("timed out")
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    answer = await service.answer("ප්‍රශ්නය කුමක්ද?", "si", [source("This is English context.")])

    assert "වැඩි වේලාවක්" in answer
    assert "OLLAMA_TIMEOUT_SECONDS" in answer


@pytest.mark.asyncio
async def test_sinhala_question_with_english_context_returns_english_fallback(
    monkeypatch: pytest.MonkeyPatch,
    service: LLMService,
) -> None:
    FakeAsyncClient.payloads = []
    FakeAsyncClient.exception = httpx.ConnectError("connection failed")
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    answer = await service.answer(
        "Earth \u0d9c\u0dd0\u0db1 \u0d9a\u0dd2\u0dba\u0db1\u0dca\u0db1\u0dda \u0d9a\u0dd4\u0db8\u0d9a\u0dca\u0daf?",
        "en",
        [source("This is English context.")],
    )

    assert answer.startswith("The local LLM service is unavailable")


@pytest.mark.asyncio
async def test_connection_failure_returns_unavailable_fallback(
    monkeypatch: pytest.MonkeyPatch,
    service: LLMService,
) -> None:
    FakeAsyncClient.payloads = []
    FakeAsyncClient.exception = httpx.ConnectError("connection failed")
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    answer = await service.answer("What is this about?", "en", [source("This is English context.")])

    assert answer.startswith("The local LLM service is unavailable")
