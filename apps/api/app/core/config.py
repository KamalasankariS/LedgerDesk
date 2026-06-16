"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = (
        "postgresql+asyncpg://ledgerdesk:ledgerdesk_dev@localhost:5433/ledgerdesk"
    )
    database_url_sync: str = (
        "postgresql://ledgerdesk:ledgerdesk_dev@localhost:5433/ledgerdesk"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o"

    # App
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = ""
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Demo user IDs (for MVP without full auth flow)
    demo_user_id: str = "00000000-0000-0000-0000-000000000001"
    demo_analyst_id: str = "00000000-0000-0000-0000-000000000002"

    # Agent settings
    confidence_threshold: float = 0.7
    grounding_threshold: float = 0.5
    max_tool_calls: int = 10
    tool_timeout_seconds: int = 30

    model_config = {"env_file": ".env", "extra": "allow"}


settings = Settings()
