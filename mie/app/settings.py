from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    mie_model: str = "openai:gpt-5.5"
    mie_default_campaign: str = "CAMP-0001"

    crawl4ai_base_url: str = "http://crawl4ai:11235"
    crawl4ai_api_token: str = ""
    crawl_timeout_seconds: float = 120.0
    crawl_poll_seconds: float = 1.0
    crawl_poll_attempts: int = 30

    agentos_db_file: str = "/data/agentos.db"

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
