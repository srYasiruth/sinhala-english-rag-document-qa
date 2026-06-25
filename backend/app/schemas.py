from datetime import datetime

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: str
    language_mix: str
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceOut(BaseModel):
    chunk_id: str
    document_id: int | None = None
    filename: str
    page_number: int | None = None
    text: str
    score: float
    highlights: list[str] = Field(default_factory=list)


class QueryIn(BaseModel):
    question: str = Field(min_length=1)
    document_ids: list[int] | None = None
    summarize: bool = False


class QueryOut(BaseModel):
    question: str
    question_language: str
    answer: str
    confidence: float
    sources: list[SourceOut]


class ConversationOut(BaseModel):
    id: int
    question: str
    answer: str
    question_language: str
    confidence: float
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminStatsOut(BaseModel):
    documents: int
    chunks: int
    conversations: int
    retrieval_logs: int


class RetrievalLogOut(BaseModel):
    id: int
    conversation_id: int | None
    question: str
    document_id: int | None
    chunk_id: str
    score: float
    created_at: datetime

    model_config = {"from_attributes": True}
