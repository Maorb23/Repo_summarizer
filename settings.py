# /settings.py
# This file defines the configuration settings for the Repo Summarizer API.
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Repo Summarizer API"

    # GitHub
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    github_api_base: str = "https://api.github.com"
    http_timeout_s: float = 20.0

    # Repo processing / context management
    max_files: int = 14
    max_file_bytes: int = 80_000          # per file hard cap
    max_total_context_chars: int = 45_000  # total prompt budget (approx chars)
    max_readme_chars: int = 18_000
    max_tree_items: int = 6_000            # safety on huge repos

    # Nebius Token Factory (OpenAI-compatible)
    nebius_api_key: str | None = Field(default=None, alias="NEBIUS_API_KEY")
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    nebius_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct"
    llm_max_tokens: int = 700
    llm_temperature: float = 0.2

    # Caching
    cache_ttl_seconds: int = 600

    # Optional Django UI (basic)
    enable_django_ui: bool = Field(default=False, alias="ENABLE_DJANGO_UI")


settings = Settings()