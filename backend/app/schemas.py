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
    language_mix: str = "unknown"
    highlights: list[str] = Field(default_factory=list)


class QueryIn(BaseModel):
    question: str = Field(min_length=1)
    document_ids: list[int] | None = None
    summarize: bool = False
    debug: bool = False


class RetrievalDebugOut(BaseModel):
    question_language: str
    target_document_languages: list[str] = Field(default_factory=list)
    query_variants: list[str] = Field(default_factory=list)
    translated_queries: list[str] = Field(default_factory=list)
    candidate_chunks: list[dict] = Field(default_factory=list)
    final_chunks: list[dict] = Field(default_factory=list)
    answer_language: str


class QueryOut(BaseModel):
    question: str
    question_language: str
    answer_language: str
    answer: str
    confidence: float
    sources: list[SourceOut]
    debug: RetrievalDebugOut | None = None


class ConversationOut(BaseModel):
    id: int
    question: str
    answer: str
    question_language: str
    answer_language: str | None = None
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
