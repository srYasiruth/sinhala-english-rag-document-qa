import pytest
from chromadb.errors import InvalidDimensionException

from app.errors import IndexingError
from app.vector_store import VectorStore, collection_name_for_model


def test_collection_name_for_model_is_model_specific() -> None:
    e5 = collection_name_for_model("intfloat/multilingual-e5-base")
    minilm = collection_name_for_model("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    assert e5 == "document_chunks_intfloat_multilingual_e5_base"
    assert minilm == "document_chunks_sentence_transformers_paraphrase_multilingual_minilm_l12_v2"
    assert e5 != minilm


def test_add_chunks_dimension_mismatch_returns_indexing_error() -> None:
    class FakeCollection:
        def add(self, **_: object) -> None:
            raise InvalidDimensionException("bad dimensions")

    store = VectorStore.__new__(VectorStore)
    store.collection = FakeCollection()

    with pytest.raises(IndexingError, match="different model"):
        store.add_chunks(ids=["c1"], texts=["text"], embeddings=[[0.1]], metadatas=[{}])
