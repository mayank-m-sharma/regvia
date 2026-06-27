from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", ".env.local", ".env.prod"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "local"  # "local" | "production"

    DATABASE_URL: str = "postgresql+asyncpg://regvia:regvia@localhost:5432/regvia"

    S3_BUCKET_NAME: str = "regvia-documents"
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_ENDPOINT_URL: str = ""  # empty = real AWS, set to MinIO URL for local dev

    # Embedding provider — OpenAI takes priority if key is set; falls back to
    # Ollama when APP_ENV=local. Production always requires OPENAI_API_KEY.
    OPENAI_API_KEY: str = ""
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536  # 1536 for OpenAI; 768 for nomic-embed-text

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OLLAMA_CHAT_MODEL: str = "llama3.2"  # any model pulled via `ollama pull`

    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"

    OPENAI_SUMMARY_MODEL: str = "gpt-4o-mini"  # used for summary generation
    OLLAMA_SUMMARY_MODEL: str = "llama3.2"  # local fallback
    SUMMARY_DIRECT_CHUNK_LIMIT: int = 30  # docs <= this use direct strategy

    LOG_LEVEL: str = "INFO"  # DEBUG for verbose LLM output, INFO for normal

    # Background task queue
    USE_CELERY: bool = False  # True = Celery+Redis; False = FastAPI BackgroundTasks
    REDIS_URL: str = "redis://localhost:6379/0"


settings = Settings()
