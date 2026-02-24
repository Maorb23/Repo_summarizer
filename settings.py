# /settings.py
# This file defines the configuration settings for the Repo Summarizer API.
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8") # Create .env file in project root with NEBIUS and GITHUB tokens.

    app_name: str = "Repo Summarizer API"

    # GitHub
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN") # From .env, for higher rate limits.
    github_api_base: str = "https://api.github.com"
    http_timeout_s: float = 10.0

    # Repo processing / context management
    max_files: int = 14 # Max files the processor will select for LLM context. we score and prioritize files to pick the most relevant ones within this limit.
    max_file_bytes: int = 80_000          # Per file limit of bytes to consider.
    max_total_context_chars: int = 45_000  # Total prompt budget (approx chars)
    max_readme_chars: int = 18_000 # README files can be large but are often very informative, so we allow a bigger chunk for them.
    max_tree_items: int = 6_000  # Safety on huge repos. Limit the number of items we process from the repo tree.

    # Nebius Token Factory (OpenAI-compatible)
    nebius_api_key: str | None = Field(default=None, alias="NEBIUS_API_KEY") # From .env.
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    nebius_model: str = "Qwen/Qwen3-30B-A3B-Instruct-2507"
    llm_max_tokens: int = 700 # Max tokens for LLM output (summary + metadata). Adjust based on your needs and model limits.
    llm_temperature: float = 0.2 # Lower temperature for more focused summaries, but still some creativeness.

    # Caching
    cache_ttl_seconds: int = 600

    # Optional Django UI (basic)
    enable_django_ui: bool = Field(default=False, alias="ENABLE_DJANGO_UI")


settings = Settings()