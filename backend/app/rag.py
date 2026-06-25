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
from app.text_processing import chunk_text, detect_language, detect_question_language, keywords_for_highlight
from app.vector_store import get_vector_store


SUPPORTED_EXTENSIONS = {"pdf", "docx", "txt"}


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

    embeddings = get_embedding_service().embed([chunk.text for chunk in all_chunks])
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
    query_embedding = get_embedding_service().embed([payload.question])[0]
    rows = get_vector_store().query(
        query_embedding=query_embedding,
        top_k=settings.retrieval_top_k,
        document_ids=payload.document_ids,
    )
    highlights = keywords_for_highlight(payload.question)
    sources = [
        SourceOut(
            chunk_id=row["chunk_id"],
            document_id=row["metadata"].get("document_id"),
            filename=row["metadata"].get("filename", "unknown"),
            page_number=row["metadata"].get("page_number") or None,
            text=row["text"],
            score=row["score"],
            highlights=[word for word in highlights if word.lower() in row["text"].lower()],
        )
        for row in rows
    ]
    confidence = round(sum(source.score for source in sources) / len(sources), 4) if sources else 0.0
    answer = await LLMService().answer(payload.question, question_language, sources, payload.summarize)

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
        answer=answer,
        confidence=confidence,
        sources=sources,
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


def admin_counts(db: Session) -> dict[str, int]:
    return {
        "documents": db.scalar(func.count(Document.id)) or 0,
        "chunks": db.scalar(func.count(Chunk.id)) or 0,
        "conversations": db.scalar(func.count(Conversation.id)) or 0,
        "retrieval_logs": db.scalar(func.count(RetrievalLog.id)) or 0,
    }
