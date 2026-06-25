import httpx

from app.config import get_settings
from app.schemas import SourceOut
from app.text_processing import answer_language_name


INSUFFICIENT = {
    "si": "උඩුගත කළ ලේඛනවල මෙම ප්‍රශ්නයට පිළිතුරු දීමට ප්‍රමාණවත් තොරතුරු නොමැත.",
    "en": "The uploaded documents do not contain enough information to answer this question.",
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
        except Exception:
            return self._extractive_fallback(question_language, sources)

    def _build_prompt(
        self,
        question: str,
        question_language: str,
        sources: list[SourceOut],
        summarize: bool,
    ) -> str:
        language_name = answer_language_name(question_language)
        context = "\n\n".join(
            f"[Source {idx + 1} | {source.filename} | page {source.page_number or 'N/A'}]\n{source.text}"
            for idx, source in enumerate(sources)
        )
        summary_instruction = "Include a short summary after the answer." if summarize else "Do not add a separate summary."
        return f"""You are a document question-answering assistant.
Answer only using the provided context. If the answer is not present, say there is not enough information.
Answer in {language_name}. {summary_instruction}

Context:
{context}

Question:
{question}

Answer:"""

    async def _ollama_generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.settings.ollama_base_url}/api/generate",
                json={
                    "model": self.settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "top_p": 0.9},
                },
            )
            response.raise_for_status()
            data = response.json()
            answer = str(data.get("response", "")).strip()
            if not answer:
                raise RuntimeError("Empty Ollama response")
            return answer

    def _extractive_fallback(self, question_language: str, sources: list[SourceOut]) -> str:
        if question_language == "si":
            return (
                "දේශීය LLM සේවාව නොලැබෙන නිසා සම්පූර්ණ ජනන පිළිතුරක් ලබා දිය නොහැක. "
                "කරුණාකර Ollama ක්‍රියාත්මක කර Qwen ආකෘතිය සක්‍රීය කර නැවත උත්සාහ කරන්න. "
                "අදාළ මූලාශ්‍ර කොටස් පහත citations ලෙස පෙන්වා ඇත."
            )
        return (
            "The local LLM service is unavailable, so a complete generated answer cannot be produced. "
            "Please start Ollama with the Qwen model and try again. "
            "The relevant source passages are shown in the citations below."
        )
