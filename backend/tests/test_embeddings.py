from app.embeddings import EmbeddingService


def service_for(model_name: str) -> EmbeddingService:
    service = EmbeddingService.__new__(EmbeddingService)
    service.model_name = model_name
    return service


def test_e5_prefixes_passages_and_queries() -> None:
    service = service_for("intfloat/multilingual-e5-base")

    assert service.prepare_texts(["Document text"], "passage") == ["passage: Document text"]
    assert service.prepare_texts(["User question"], "query") == ["query: User question"]


def test_non_e5_models_do_not_add_prefixes() -> None:
    service = service_for("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    assert service.prepare_texts(["Document text"], "passage") == ["Document text"]
    assert service.prepare_texts(["User question"], "query") == ["User question"]
