import logging

import httpx

from app.config import get_settings
from app.schemas import SourceOut
from app.text_processing import answer_language_name


logger = logging.getLogger(__name__)

INSUFFICIENT = {
    "si": "උඩුගත කළ ලේඛනවල මෙම ප්‍රශ්නයට පිළිතුරු දීමට ප්‍රමාණවත් තොරතුරු නොමැත.",
    "en": "The uploaded documents do not contain enough information to answer this question.",
}

FALLBACKS = {
    "timeout": {
        "si": (
            "දේශීය LLM ආකෘතිය පිළිතුර සෑදීමට වැඩි වේලාවක් ගත කළා. "
            "කරුණාකර OLLAMA_TIMEOUT_SECONDS අගය වැඩි කර නැවත උත්සාහ කරන්න. "
            "අදාළ මූලාශ්‍ර කොටස් පහත citations ලෙස පෙන්වා ඇත."
        ),
        "en": (
            "The local LLM took too long to generate an answer. Increase OLLAMA_TIMEOUT_SECONDS "
            "and try again. The relevant source passages are shown in the citations below."
        ),
    },
    "unavailable": {
        "si": (
            "දේශීය LLM සේවාව සමඟ සම්බන්ධ වීමට නොහැක. "
            "කරුණාකර Ollama ක්‍රියාත්මක දැයි සහ Qwen ආකෘතිය තිබේදැයි පරීක්ෂා කර නැවත උත්සාහ කරන්න. "
            "අදාළ මූලාශ්‍ර කොටස් පහත citations ලෙස පෙන්වා ඇත."
        ),
        "en": (
            "The local LLM service is unavailable, so a complete generated answer cannot be produced. "
            "Please start Ollama with the Qwen model and try again. "
            "The relevant source passages are shown in the citations below."
        ),
    },
}


class LLMService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def answer(
        self,
        question: str,
        question_language: str,
        sources: list[SourceOut],
        summarize: bool = False,
    ) -> str:
        if not sources:
            return INSUFFICIENT.get(question_language, INSUFFICIENT["en"])

        prompt = self._build_prompt(question, question_language, sources, summarize)
        try:
            return await self._ollama_generate(prompt)
        except httpx.TimeoutException:
            logger.exception("Ollama timed out while generating an answer.")
            return self._fallback(question_language, "timeout")
        except (httpx.HTTPError, RuntimeError):
            logger.exception("Ollama failed while generating an answer.")
            return self._fallback(question_language, "unavailable")
        except Exception:
            logger.exception("Unexpected LLM generation failure.")
            return self._fallback(question_language, "unavailable")

    def _build_prompt(
        self,
        question: str,
        question_language: str,
        sources: list[SourceOut],
        summarize: bool,
    ) -> str:
        language_name = answer_language_name(question_language)
        context = self._build_context(sources)
        summary_instruction = "Include a short summary after the answer." if summarize else "Do not add a separate summary."
        return f"""You are a document question-answering assistant.
Answer only using the provided context. If the answer is not present, say there is not enough information.
Answer in {language_name}. {summary_instruction}

Context:
{context}

Question:
{question}

Answer:"""

    def _build_context(self, sources: list[SourceOut]) -> str:
        parts: list[str] = []
        used_chars = 0
        max_context_chars = self.settings.max_context_chars
        max_source_chars = self.settings.max_source_chars

        for idx, source in enumerate(sources):
            source_text = source.text[:max_source_chars].strip()
            part = f"[Source {idx + 1} | {source.filename} | page {source.page_number or 'N/A'}]\n{source_text}"
            remaining = max_context_chars - used_chars
            if remaining <= 0:
                break
            if len(part) > remaining:
                part = part[:remaining].rstrip()
            parts.append(part)
            used_chars += len(part) + 2

        return "\n\n".join(parts)

    async def _ollama_generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=self.settings.ollama_timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.ollama_base_url}/api/generate",
                json={
                    "model": self.settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": self.settings.ollama_keep_alive,
                    "options": {"temperature": 0.1, "top_p": 0.9},
                },
            )
            response.raise_for_status()
            data = response.json()
            answer = str(data.get("response", "")).strip()
            if not answer:
                raise RuntimeError("Empty Ollama response")
            return answer

    def _fallback(self, question_language: str, reason: str) -> str:
        messages = FALLBACKS.get(reason, FALLBACKS["unavailable"])
        return messages.get(question_language, messages["en"])
