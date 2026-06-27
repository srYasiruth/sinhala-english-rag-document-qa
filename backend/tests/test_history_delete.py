from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Conversation, RetrievalLog
from app.rag import clear_conversations, delete_conversation


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def add_conversation(db, question: str = "Question?") -> Conversation:
    conversation = Conversation(question=question, answer="Answer.", question_language="en", confidence=0.8)
    db.add(conversation)
    db.flush()
    db.add(RetrievalLog(conversation_id=conversation.id, question=question, document_id=1, chunk_id="c1", score=0.9))
    db.commit()
    db.refresh(conversation)
    return conversation


def test_delete_conversation_removes_linked_retrieval_logs() -> None:
    db = make_db()
    conversation = add_conversation(db)

    assert delete_conversation(conversation.id, db) is True

    assert db.query(Conversation).count() == 0
    assert db.query(RetrievalLog).count() == 0


def test_delete_conversation_returns_false_for_missing_item() -> None:
    db = make_db()

    assert delete_conversation(999, db) is False


def test_clear_conversations_removes_all_history_and_retrieval_logs() -> None:
    db = make_db()
    add_conversation(db, "Question 1?")
    add_conversation(db, "Question 2?")

    assert clear_conversations(db) == 2
    assert db.query(Conversation).count() == 0
    assert db.query(RetrievalLog).count() == 0
