import re
import unicodedata
from dataclasses import dataclass


SINHALA_RE = re.compile(r"[\u0D80-\u0DFF]")
LATIN_RE = re.compile(r"[A-Za-z]")
WORD_RE = re.compile(r"[\w\u0D80-\u0DFF]+", re.UNICODE)


@dataclass(frozen=True)
class TextChunk:
    text: str
    chunk_index: int
    page_number: int | None
    token_count: int
    language_mix: str


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_language(text: str) -> str:
    sinhala = len(SINHALA_RE.findall(text))
    latin = len(LATIN_RE.findall(text))
    total = sinhala + latin
    if total == 0:
        return "unknown"
    sinhala_ratio = sinhala / total
    if sinhala_ratio >= 0.65:
        return "si"
    if sinhala_ratio <= 0.15:
        return "en"
    return "mixed"


def detect_question_language(text: str) -> str:
    sinhala = len(SINHALA_RE.findall(text))
    latin = len(LATIN_RE.findall(text))
    if sinhala > 0:
        return "si"
    if latin > 0:
        return "en"
    return "en"


def answer_language_name(lang_code: str) -> str:
    return "Sinhala" if lang_code == "si" else "English"


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text)


def chunk_text(
    text: str,
    chunk_size_tokens: int = 500,
    chunk_overlap_tokens: int = 50,
    page_number: int | None = None,
) -> list[TextChunk]:
    normalized = normalize_text(text)
    tokens = tokenize(normalized)
    if not tokens:
        return []

    chunks: list[TextChunk] = []
    step = max(1, chunk_size_tokens - chunk_overlap_tokens)
    for index, start in enumerate(range(0, len(tokens), step)):
        token_slice = tokens[start : start + chunk_size_tokens]
        if not token_slice:
            continue
        chunk = " ".join(token_slice)
        chunks.append(
            TextChunk(
                text=chunk,
                chunk_index=index,
                page_number=page_number,
                token_count=len(token_slice),
                language_mix=detect_language(chunk),
            )
        )
        if start + chunk_size_tokens >= len(tokens):
            break
    return chunks


def keywords_for_highlight(question: str, limit: int = 8) -> list[str]:
    words = [w for w in tokenize(question) if len(w) > 2]
    seen: set[str] = set()
    unique: list[str] = []
    for word in words:
        key = word.lower()
        if key not in seen:
            unique.append(word)
            seen.add(key)
        if len(unique) >= limit:
            break
    return unique
