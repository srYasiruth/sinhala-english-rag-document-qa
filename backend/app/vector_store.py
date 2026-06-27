from functools import lru_cache
import re

import chromadb
from chromadb.errors import InvalidDimensionException
from chromadb.api.models.Collection import Collection

from app.config import get_settings
from app.errors import IndexingError


def collection_name_for_model(model_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", model_name.lower()).strip("_")
    return f"document_chunks_{slug}"


class VectorStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        self.collection_name = collection_name_for_model(settings.embedding_model)
        self.collection: Collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine", "embedding_model": settings.embedding_model},
        )

    def add_chunks(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        if not ids:
            return
        try:
            self.collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
        except InvalidDimensionException as exc:
            raise IndexingError(
                "The vector database contains embeddings from a different model. "
                "Delete and re-upload documents after changing EMBEDDING_MODEL, or use the same embedding model as before."
            ) from exc

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        document_ids: list[int] | None = None,
    ) -> list[dict]:
        where = {"document_id": {"$in": document_ids}} if document_ids else None
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        rows: list[dict] = []
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for idx, chunk_id in enumerate(ids):
            distance = float(distances[idx]) if idx < len(distances) else 1.0
            rows.append(
                {
                    "chunk_id": chunk_id,
                    "text": docs[idx] if idx < len(docs) else "",
                    "metadata": metadatas[idx] if idx < len(metadatas) else {},
                    "distance": distance,
                    "score": max(0.0, 1.0 - distance),
                }
            )
        return rows

    def delete_document(self, document_id: int) -> None:
        self.collection.delete(where={"document_id": document_id})


@lru_cache
def get_vector_store() -> VectorStore:
    return VectorStore()
