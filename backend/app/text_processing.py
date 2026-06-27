import re
import unicodedata
from dataclasses import dataclass


SINHALA_RE = re.compile(r"[\u0D80-\u0DFF]")
LATIN_RE = re.compile(r"[A-Za-z]")
WORD_RE = re.compile(r"[\w\u0D80-\u0DFF]+", re.UNICODE)
PAGE_NUMBER_RE = re.compile(r"^\s*(?:page\s*)?\d+\s*$", re.IGNORECASE)
ENGLISH_ANSWER_REQUEST_RE = re.compile(
    r"\b(?:answer|reply|respond|response|final answer)\s+(?:in|with)\s+english\b|\benglish\s+(?:වලින්|භාෂාවෙන්)|ඉංග්‍රීසියෙන්",
    re.IGNORECASE,
)
SINHALA_ANSWER_REQUEST_RE = re.compile(
    r"\b(?:answer|reply|respond|response|final answer)\s+(?:in|with)\s+sinhala\b|\bsinhala\s+(?:වලින්|භාෂාවෙන්)|සිංහලෙන්",
    re.IGNORECASE,
)


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
    text = remove_repeated_noise(text)
    text = re.sub(r"(?<![.!?:;\u0DF4])\n(?!\n)", " ", text)
    text = re.sub(r"\n\n[ \t]+", "\n\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_repeated_noise(text: str) -> str:
    lines = [line.strip() for line in text.split("\n")]
    non_empty_counts: dict[str, int] = {}
    for line in lines:
        if line:
            non_empty_counts[line] = non_empty_counts.get(line, 0) + 1

    cleaned: list[str] = []
    for line in lines:
        if PAGE_NUMBER_RE.match(line):
            continue
        if line and len(line) <= 120 and non_empty_counts.get(line, 0) >= 3:
            continue
        cleaned.append(line)

    return "\n".join(cleaned)


def detect_language(text: str) -> str:
    sinhala = len(SINHALA_RE.findall(text))
    latin = len(LATIN_RE.findall(text))
    total = sinhala + latin
    if total == 0:
        return "unknown"
    sinhala_ratio = sinhala / total
    if sinhala_ratio >= 0.65:
        return "si"
    if sinhala_ratio <= 0.05:
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


def determine_requested_answer_language(text: str) -> str:
    if ENGLISH_ANSWER_REQUEST_RE.search(text):
        return "en"
    if SINHALA_ANSWER_REQUEST_RE.search(text):
        return "si"
    return detect_question_language(text)


def answer_language_name(lang_code: str) -> str:
    return "Sinhala" if lang_code == "si" else "English"


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text)


def split_paragraphs(text: str) -> list[str]:
    normalized = normalize_text(text)
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", normalized) if paragraph.strip()]
    return paragraphs or ([normalized] if normalized else [])


def chunk_tokens(tokens: list[str], chunk_size_tokens: int, chunk_overlap_tokens: int) -> list[list[str]]:
    chunks: list[list[str]] = []
    step = max(1, chunk_size_tokens - chunk_overlap_tokens)
    for start in range(0, len(tokens), step):
        token_slice = tokens[start : start + chunk_size_tokens]
        if token_slice:
            chunks.append(token_slice)
        if start + chunk_size_tokens >= len(tokens):
            break
    return chunks


def chunk_text(
    text: str,
    chunk_size_tokens: int = 500,
    chunk_overlap_tokens: int = 50,
    page_number: int | None = None,
) -> list[TextChunk]:
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        return []

    packed_chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens: list[str] = []

    def flush_current() -> None:
        nonlocal current_parts, current_tokens
        if current_parts:
            packed_chunks.append("\n\n".join(current_parts).strip())
        current_parts = []
        current_tokens = []

    for paragraph in paragraphs:
        paragraph_tokens = tokenize(paragraph)
        if not paragraph_tokens:
            continue
        if len(paragraph_tokens) > chunk_size_tokens:
            flush_current()
            for token_slice in chunk_tokens(paragraph_tokens, chunk_size_tokens, chunk_overlap_tokens):
                packed_chunks.append(" ".join(token_slice))
            continue
        if current_parts and len(current_tokens) + len(paragraph_tokens) > chunk_size_tokens:
            flush_current()
        current_parts.append(paragraph)
        current_tokens.extend(paragraph_tokens)

    flush_current()

    chunks: list[TextChunk] = []
    for index, chunk in enumerate(packed_chunks):
        token_slice = tokenize(chunk)
        if not token_slice:
            continue
        chunks.append(
            TextChunk(
                text=chunk,
                chunk_index=index,
                page_number=page_number,
                token_count=len(token_slice),
                language_mix=detect_language(chunk),
            )
        )
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
