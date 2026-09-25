
from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Change Start
    # Neo4j Configuration
    neo4j_uri: str = Field(validation_alias="NEO4J_URI")
    neo4j_username: str = Field(validation_alias="NEO4J_USERNAME")
    neo4j_password: str = Field(validation_alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(
        default="neo4j",
        validation_alias="NEO4J_DATABASE",
    )
    cors_origins: str = Field(
        default=(
            "http://localhost:5173,"
            "http://127.0.0.1:5173"
        ),
        validation_alias="CORS_ORIGINS",
    )

    # PostgreSQL Configuration
    postgres_host: str = Field(
        default="localhost",
        validation_alias="POSTGRES_HOST",
    )
    postgres_port: int = Field(
        default=5432,
        validation_alias="POSTGRES_PORT",
    )
    postgres_database: str = Field(
        default="aact_full",
        validation_alias="POSTGRES_DATABASE",
    )
    postgres_username: str = Field(
        validation_alias="POSTGRES_USERNAME",
    )
    postgres_password: str = Field(
        validation_alias="POSTGRES_PASSWORD",
    )
    postgres_schema: str = Field(
        default="ctgov",
        validation_alias="POSTGRES_SCHEMA",
    )
    # Change End
        # Change Start
    # LLM Configuration
    llm_provider: Literal[
        "auto",
        "openai",
        "gemini",
        "openrouter",
    ] = Field(
        default="auto",
        validation_alias="LLM_PROVIDER",
    )
    llm_provider_priority: str = Field(
        default="openai,gemini,openrouter",
        validation_alias="LLM_PROVIDER_PRIORITY",
    )
    llm_startup_probe: bool = Field(
        default=True,
        validation_alias="LLM_STARTUP_PROBE",
    )
    llm_request_timeout_seconds: float = Field(
        default=20.0,
        gt=0,
        le=60,
        validation_alias="LLM_REQUEST_TIMEOUT_SECONDS",
    )
    llm_max_retries: int = Field(
        default=0,
        ge=0,
        le=2,
        validation_alias="LLM_MAX_RETRIES",
    )

    # OpenRouter
    openrouter_api_key: str | None = Field(
        default=None,
        validation_alias="OPENROUTER_API_KEY",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias="OPENROUTER_BASE_URL",
    )
    openrouter_model: str | None = Field(
        default=None,
        validation_alias="OPENROUTER_MODEL",
    )

    # Google Gemini
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias="GEMINI_API_KEY",
    )
    gemini_model: str | None = Field(
        default=None,
        validation_alias="GEMINI_MODEL",
    )

    # OpenAI
    openai_api_key: str | None = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
    )
    openai_model: str | None = Field(
        default=None,
        validation_alias="OPENAI_MODEL",
    )
    # Change End


@lru_cache
def get_settings() -> Settings:
    """Return a cached application settings instance."""
    return Settings()


def get_cors_origins(settings: Settings | None = None) -> list[str]:
    """Return the configured, non-empty CORS origin allow-list."""

    resolved_settings = settings or get_settings()
    return [
        origin.strip()
        for origin in resolved_settings.cors_origins.split(",")
        if origin.strip()
    ]


def get_llm_provider_priority(settings: Settings | None = None) -> list[str]:
    """Return validated, de-duplicated provider priority in configured order."""
    resolved_settings = settings or get_settings()
    allowed = {"openai", "gemini", "openrouter"}
    providers: list[str] = []
    for raw in resolved_settings.llm_provider_priority.split(","):
        provider = raw.strip().lower()
        if provider in allowed and provider not in providers:
            providers.append(provider)
    for provider in ("openai", "gemini", "openrouter"):
        if provider not in providers:
            providers.append(provider)
    return providers
