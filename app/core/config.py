"""
Application configuration using pydantic-settings.
All values are loaded from environment variables (or .env file).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@postgres:5432/scalency"

    # Redis / Celery
    REDIS_URL: str = "redis://redis:6379"

    # AI
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"  # cost-effective default

    # Security
    SECRET_KEY: str = "change-me-in-production"

    # App
    APP_TITLE: str = "Scalency Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
