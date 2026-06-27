from functools import lru_cache

from app.config import get_settings


class EmbeddingService:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    @property
    def uses_e5_prefixes(self) -> bool:
        return "multilingual-e5" in self.model_name.lower()

    def prepare_texts(self, texts: list[str], role: str) -> list[str]:
        if not self.uses_e5_prefixes:
            return texts
        prefix = "query: " if role == "query" else "passage: "
        return [text if text.startswith(prefix) else f"{prefix}{text}" for text in texts]

    def embed(self, texts: list[str], role: str = "passage") -> list[list[float]]:
        vectors = self.model.encode(self.prepare_texts(texts, role), normalize_embeddings=True)
        return vectors.tolist()


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(get_settings().embedding_model)
