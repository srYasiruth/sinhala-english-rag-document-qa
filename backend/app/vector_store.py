from functools import lru_cache

import chromadb
from chromadb.api.models.Collection import Collection

from app.config import get_settings


class VectorStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        self.collection: Collection = self.client.get_or_create_collection(
            name="document_chunks",
            metadata={"hnsw:space": "cosine"},
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
        self.collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

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
                    "text": docs[idx],
                    "metadata": metadatas[idx],
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
