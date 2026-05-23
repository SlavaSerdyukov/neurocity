from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NEUROCITY"
    database_url: str = "sqlite:///./neurocity.db"
    default_seed: int = 2049
    default_population: int = 5000
    default_districts: int = 14
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5"
    enable_llm: bool = False

    model_config = SettingsConfigDict(env_prefix="NEUROCITY_", env_file=".env", extra="ignore")

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent


@lru_cache
def get_settings() -> Settings:
    return Settings()

