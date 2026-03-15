"""
Application configuration using pydantic-settings.
All values are loaded from environment variables (or .env file).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./scalency.db"

    # Redis / Celery (optional for local dev)
    REDIS_URL: str = "redis://redis:6379"

    # AI
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"  # cost-effective default

    # Claude API (fallback if OpenRouter unavailable)
    CLAUDE_API_KEY: str = ""
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com/v1"  # Custom endpoint support
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"  # latest Claude model

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
