from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = Field(min_length=1)
    database_url: str = Field(min_length=1)
    default_seed: int = Field(ge=0)
    default_population: int = Field(ge=1)
    default_districts: int = Field(ge=1)
    ollama_url: str = Field(min_length=1)
    ollama_model: str = Field(min_length=1)
    enable_llm: bool

    model_config = SettingsConfigDict(
        env_prefix="NEUROCITY_",
        env_file=PROJECT_ROOT / ".env",
        extra="ignore",
    )

    @field_validator("database_url", "ollama_url", "ollama_model", mode="before")
    @classmethod
    def strip_sensitive_config(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return value.strip()

    @property
    def base_dir(self) -> Path:
        return PROJECT_ROOT


@lru_cache
def get_settings() -> Settings:
    return Settings()
