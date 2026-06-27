from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sinhala English Local RAG"
    database_url: str = "sqlite:///../data/rag.sqlite3"
    upload_dir: Path = Path("../data/uploads")
    chroma_dir: Path = Path("../data/chroma")
    embedding_model: str = "intfloat/multilingual-e5-base"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    ollama_timeout_seconds: int = 300
    ollama_keep_alive: str = "10m"
    max_context_chars: int = 12000
    max_source_chars: int = 3000
    chunk_size_tokens: int = 700
    chunk_overlap_tokens: int = 120
    retrieval_top_k: int = 5
    retrieval_candidate_k: int = 15
    keyword_boost: float = 0.04
    enable_query_translation: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def ensure_runtime_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        db_path = self.database_url.replace("sqlite:///", "", 1)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_dirs()
    return settings
