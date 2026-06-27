from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.embeddings import get_embedding_service
from app.extraction import extract_text
from app.llm import LLMService
from app.models import Chunk, Conversation, Document, RetrievalLog
from app.schemas import QueryIn, QueryOut, SourceOut
from app.text_processing import (
    chunk_text,
    detect_language,
    detect_question_language,
    determine_requested_answer_language,
    keywords_for_highlight,
)
from app.vector_store import get_vector_store


SUPPORTED_EXTENSIONS = {"pdf", "docx", "txt"}
SUPPORTED_ANSWER_LANGUAGES = {"si", "en"}


def determine_answer_language(sources: list[SourceOut]) -> str:
    counts = {"si": 0, "en": 0}
    for source in sources:
        if source.language_mix in SUPPORTED_ANSWER_LANGUAGES:
            counts[source.language_mix] += 1

    majority_threshold = len(sources) / 2
    if counts["si"] > majority_threshold:
        return "si"
    if counts["en"] > majority_threshold:
        return "en"

    for source in sources:
        if source.language_mix in SUPPORTED_ANSWER_LANGUAGES:
            return source.language_mix
        detected_language = detect_language(source.text)
        if detected_language in SUPPORTED_ANSWER_LANGUAGES:
            return detected_language

    return "en"


def source_from_retrieval_row(row: dict, highlights: list[str]) -> SourceOut:
    metadata = row.get("metadata") or {}
    text = row.get("text") or ""
    return SourceOut(
        chunk_id=str(row.get("chunk_id") or "unknown-chunk"),
        document_id=metadata.get("document_id"),
        filename=metadata.get("filename", "unknown"),
        page_number=metadata.get("page_number") or None,
        text=text,
        score=float(row.get("score") or 0.0),
        language_mix=metadata.get("language_mix", "unknown"),
        highlights=[word for word in highlights if word.lower() in text.lower()],
    )


def target_document_languages(db: Session, document_ids: list[int] | None = None) -> list[str]:
    query = db.query(Document.language_mix)
    if document_ids:
        query = query.filter(Document.id.in_(document_ids))

    languages: set[str] = set()
    for (language_mix,) in query.distinct().all():
        if language_mix in SUPPORTED_ANSWER_LANGUAGES:
            languages.add(language_mix)
        elif language_mix == "mixed":
            languages.update(SUPPORTED_ANSWER_LANGUAGES)

    return sorted(languages) or ["en"]


async def build_query_variants(question: str, question_language: str, target_languages: list[str]) -> tuple[list[str], list[str]]:
    variants = [question]
    translated_queries: list[str] = []
    settings = get_settings()
    if not settings.enable_query_translation:
        return variants, translated_queries

    llm = LLMService()
    for target_language in target_languages:
        if target_language == question_language:
            continue
        translated = await llm.translate_query(question, target_language)
        if translated and translated not in variants:
            variants.append(translated)
            translated_queries.append(translated)

    return variants, translated_queries


def keyword_score(text: str, terms: list[str], boost: float) -> float:
    lowered = text.lower()
    matches = sum(1 for term in terms if term.lower() in lowered)
    return matches * boost


def keyword_retrieval_rows(db: Session, terms: list[str], document_ids: list[int] | None, limit: int) -> list[dict]:
    if not terms:
        return []

    query = db.query(Chunk)
    if document_ids:
        query = query.filter(Chunk.document_id.in_(document_ids))

    rows: list[dict] = []
    for chunk in query.all():
        boost = keyword_score(chunk.text, terms, get_settings().keyword_boost)
        if boost <= 0:
            continue
        rows.append(
            {
                "chunk_id": chunk.chroma_id,
                "text": chunk.text,
                "metadata": {
                    "document_id": chunk.document_id,
                    "filename": chunk.document.original_filename if chunk.document else "unknown",
                    "page_number": chunk.page_number or 0,
                    "chunk_index": chunk.chunk_index,
                    "language_mix": chunk.language_mix,
                },
                "distance": max(0.0, 1.0 - boost),
                "score": min(0.95, boost),
                "retrieval_method": "keyword",
            }
        )

    return sorted(rows, key=lambda row: row["score"], reverse=True)[:limit]


def merge_retrieval_rows(rows: list[dict], top_k: int) -> list[dict]:
    merged: dict[str, dict] = {}
    for row in rows:
        chunk_id = str(row.get("chunk_id") or "unknown-chunk")
        existing = merged.get(chunk_id)
        if not existing or float(row.get("score") or 0.0) > float(existing.get("score") or 0.0):
            merged[chunk_id] = row
    return sorted(merged.values(), key=lambda row: float(row.get("score") or 0.0), reverse=True)[:top_k]


async def ingest_document(upload: UploadFile, db: Session) -> Document:
    settings = get_settings()
    original = upload.filename or "document.txt"
    extension = Path(original).suffix.lower().lstrip(".")
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only PDF, DOCX, and TXT files are supported.")

    stored_name = f"{uuid4().hex}.{extension}"
    stored_path = settings.upload_dir / stored_name
    content = await upload.read()
    stored_path.write_bytes(content)

    pages = extract_text(stored_path, extension)
    if not pages:
        raise ValueError("No readable text was found in the uploaded document.")

    document = Document(
        filename=stored_name,
        original_filename=original,
        file_type=extension,
        path=str(stored_path),
        language_mix=detect_language("\n".join(text for _, text in pages)),
    )
    db.add(document)
    db.flush()

    all_chunks = []
    for page_number, page_text in pages:
        for chunk in chunk_text(
            page_text,
            chunk_size_tokens=settings.chunk_size_tokens,
            chunk_overlap_tokens=settings.chunk_overlap_tokens,
            page_number=page_number,
        ):
            all_chunks.append(chunk)
    if not all_chunks:
        raise ValueError("No indexable text chunks were found in the uploaded document.")

    embeddings = get_embedding_service().embed([chunk.text for chunk in all_chunks], role="passage")
    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict] = []

    for index, chunk in enumerate(all_chunks):
        chroma_id = f"doc-{document.id}-chunk-{index}"
        ids.append(chroma_id)
        texts.append(chunk.text)
        metadatas.append(
            {
                "document_id": document.id,
                "filename": original,
                "page_number": chunk.page_number or 0,
                "chunk_index": index,
                "language_mix": chunk.language_mix,
            }
        )
        db.add(
            Chunk(
                document_id=document.id,
                chroma_id=chroma_id,
                chunk_index=index,
                page_number=chunk.page_number,
                text=chunk.text,
                language_mix=chunk.language_mix,
                token_count=chunk.token_count,
            )
        )

    get_vector_store().add_chunks(ids=ids, texts=texts, embeddings=embeddings, metadatas=metadatas)
    document.chunk_count = len(all_chunks)
    db.commit()
    db.refresh(document)
    return document


async def answer_question(payload: QueryIn, db: Session) -> QueryOut:
    settings = get_settings()
    question_language = detect_question_language(payload.question)
    target_languages = target_document_languages(db, payload.document_ids)
    query_variants, translated_queries = await build_query_variants(payload.question, question_language, target_languages)
    embedding_service = get_embedding_service()
    rows: list[dict] = []
    for query_text in query_variants:
        query_embedding = embedding_service.embed([query_text], role="query")[0]
        query_rows = get_vector_store().query(
            query_embedding=query_embedding,
            top_k=settings.retrieval_candidate_k,
            document_ids=payload.document_ids,
        )
        for row in query_rows:
            row["query"] = query_text
            row["retrieval_method"] = row.get("retrieval_method", "vector")
        rows.extend(query_rows)

    highlights = []
    for query_text in query_variants:
        highlights.extend(keywords_for_highlight(query_text))
    rows.extend(keyword_retrieval_rows(db, highlights, payload.document_ids, settings.retrieval_candidate_k))
    candidate_rows = list(rows)
    rows = merge_retrieval_rows(candidate_rows, settings.retrieval_top_k)
    sources = [source_from_retrieval_row(row, highlights) for row in rows]
    confidence = round(sum(source.score for source in sources) / len(sources), 4) if sources else 0.0
    answer_language = determine_requested_answer_language(payload.question)
    answer = await LLMService().answer(payload.question, answer_language, sources, payload.summarize)

    conversation = Conversation(
        question=payload.question,
        answer=answer,
        question_language=question_language,
        confidence=confidence,
    )
    db.add(conversation)
    db.flush()
    for source in sources:
        db.add(
            RetrievalLog(
                conversation_id=conversation.id,
                question=payload.question,
                document_id=source.document_id,
                chunk_id=source.chunk_id,
                score=source.score,
            )
        )
    db.commit()

    return QueryOut(
        question=payload.question,
        question_language=question_language,
        answer_language=answer_language,
        answer=answer,
        confidence=confidence,
        sources=sources,
        debug=(
            {
                "question_language": question_language,
                "target_document_languages": target_languages,
                "query_variants": query_variants,
                "translated_queries": translated_queries,
                "candidate_chunks": [
                    {
                        "chunk_id": str(row.get("chunk_id") or "unknown-chunk"),
                        "score": float(row.get("score") or 0.0),
                        "method": row.get("retrieval_method", "unknown"),
                        "query": row.get("query"),
                    }
                    for row in candidate_rows
                ],
                "final_chunks": [
                    {"chunk_id": source.chunk_id, "score": source.score, "language_mix": source.language_mix}
                    for source in sources
                ],
                "answer_language": answer_language,
            }
            if payload.debug
            else None
        ),
    )


def delete_document(document_id: int, db: Session) -> bool:
    document = db.get(Document, document_id)
    if not document:
        return False
    get_vector_store().delete_document(document_id)
    path = Path(document.path)
    if path.exists():
        path.unlink()
    db.delete(document)
    db.commit()
    return True


def delete_conversation(conversation_id: int, db: Session) -> bool:
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        return False
    db.query(RetrievalLog).filter(RetrievalLog.conversation_id == conversation_id).delete()
    db.delete(conversation)
    db.commit()
    return True


def clear_conversations(db: Session) -> int:
    count = db.scalar(func.count(Conversation.id)) or 0
    db.query(RetrievalLog).delete()
    db.query(Conversation).delete()
    db.commit()
    return count


def admin_counts(db: Session) -> dict[str, int]:
    return {
        "documents": db.scalar(func.count(Document.id)) or 0,
        "chunks": db.scalar(func.count(Chunk.id)) or 0,
        "conversations": db.scalar(func.count(Conversation.id)) or 0,
        "retrieval_logs": db.scalar(func.count(RetrievalLog.id)) or 0,
    }
