from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ReconAI API"
    environment: str = "local"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql://reconai:reconai@localhost:5432/reconai"

    model_config = SettingsConfigDict(env_prefix="RECONAI_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
