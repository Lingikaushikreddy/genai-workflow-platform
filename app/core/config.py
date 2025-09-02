from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise GenAI Platform"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["development", "production"] = "development"
    LOG_LEVEL: str = "INFO"

    # LLM
    OPENAI_API_KEY: SecretStr | None = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Vector store
    PINECONE_API_KEY: SecretStr | None = None
    PINECONE_INDEX_NAME: str = "enterprise-knowledge"

    # Retrieval / ingestion
    RETRIEVAL_K: int = 4
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150

    # Security
    # When API_KEY is set, protected routes require a matching X-API-Key header.
    # Left unset (the default) the API is open — convenient for local/mock use.
    API_KEY: SecretStr | None = None
    # Hard ceiling on request body size, enforced before the body is buffered.
    # 16 MiB comfortably fits the largest valid ingest (100 docs x 100k chars).
    MAX_REQUEST_BYTES: int = 16 * 1024 * 1024
    # In-process fixed-window rate limit per client, per minute. 0 disables it.
    # Note: per-replica, not cluster-global — treat as defense-in-depth behind a
    # gateway/ingress limiter, not a substitute for one.
    RATE_LIMIT_PER_MINUTE: int = 0

    # CORS: explicit origins only — never "*" alongside credentials
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("BACKEND_CORS_ORIGINS")
    @classmethod
    def _reject_wildcard_origin(cls, origins: list[str]) -> list[str]:
        # Credentials are always enabled on the CORS middleware, and the CORS
        # spec forbids "*" together with credentials. Enforce the invariant here
        # so a well-meaning `BACKEND_CORS_ORIGINS=["*"]` fails fast at startup
        # instead of silently reflecting arbitrary origins.
        if any(origin.strip() == "*" for origin in origins):
            raise ValueError(
                "BACKEND_CORS_ORIGINS must list explicit origins; '*' is not "
                "allowed because credentialed CORS forbids the wildcard."
            )
        return origins
