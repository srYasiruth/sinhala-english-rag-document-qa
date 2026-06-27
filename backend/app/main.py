from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.errors import IndexingError
from app.models import Conversation, Document, RetrievalLog
from app.rag import admin_counts, answer_question, clear_conversations, delete_conversation, delete_document, ingest_document
from app.schemas import (
    AdminStatsOut,
    ConversationOut,
    DocumentOut,
    QueryIn,
    QueryOut,
    RetrievalLogOut,
)

app = FastAPI(title="Sinhala English Local RAG")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/documents/upload", response_model=DocumentOut)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> Document:
    try:
        return await ingest_document(file, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IndexingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.get("/api/documents", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    return list(db.query(Document).order_by(desc(Document.created_at)).all())


@app.delete("/api/documents/{document_id}")
def remove_document(document_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    if not delete_document(document_id, db):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": True}


@app.post("/api/chat/query", response_model=QueryOut)
async def query_documents(payload: QueryIn, db: Session = Depends(get_db)) -> QueryOut:
    return await answer_question(payload, db)


@app.get("/api/chat/history", response_model=list[ConversationOut])
def chat_history(db: Session = Depends(get_db)) -> list[Conversation]:
    return list(db.query(Conversation).order_by(desc(Conversation.created_at)).limit(50).all())


@app.delete("/api/chat/history/{conversation_id}")
def remove_chat_history_item(conversation_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    if not delete_conversation(conversation_id, db):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


@app.delete("/api/chat/history")
def clear_chat_history(db: Session = Depends(get_db)) -> dict[str, int]:
    return {"deleted": clear_conversations(db)}


@app.get("/api/admin/stats", response_model=AdminStatsOut)
def stats(db: Session = Depends(get_db)) -> dict[str, int]:
    return admin_counts(db)


@app.get("/api/admin/retrieval-logs", response_model=list[RetrievalLogOut])
def retrieval_logs(db: Session = Depends(get_db)) -> list[RetrievalLog]:
    return list(db.query(RetrievalLog).order_by(desc(RetrievalLog.created_at)).limit(100).all())
