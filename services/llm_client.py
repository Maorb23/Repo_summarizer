# /services/llm_client.py
# This module defines a NebiusLLMClient class that provides methods for interacting with the Neb
from __future__ import annotations

import os
from typing import Any, Dict, List

from openai import AsyncOpenAI

from settings import settings
from utils.errors import upstream_error

# We use async coding for all Nebius interactions to allow for concurrent requests to prevent bottlenecks. 
# The AsyncOpenAI client is used for this purpose.
# Moreover, it works well with FastAPI's async nature.

class NebiusLLMClient:
    """
    Nebius Token Factory is OpenAI-compatible. Docs show using OpenAI SDK with:
      base_url="https://api.tokenfactory.nebius.com/v1/"
      api_key=NEBIUS_API_KEY
    and structured output via response_format. :contentReference[oaicite:1]{index=1}
    """
    def __init__(self) -> None:
        if not settings.nebius_api_key:
            # We'll still allow the service to run; caller can decide fallback behavior.
            self._client = None
            return

        self._client = AsyncOpenAI(
            base_url=settings.nebius_base_url,
            api_key=settings.nebius_api_key,
        )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def chat_json_schema(
        self,
        messages: List[Dict[str, str]],
        json_schema: Dict[str, Any],
        schema_name: str = "response",
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        if not self._client:
            raise upstream_error("NEBIUS_API_KEY is not set; LLM call is disabled")

        try:
            resp = await self._client.chat.completions.create(
                model=model or settings.nebius_model,
                messages=messages,
                temperature=temperature if temperature is not None else settings.llm_temperature,
                max_tokens=max_tokens or settings.llm_max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "schema": json_schema,
                        "strict": True,
                    },
                },
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            raise upstream_error(f"Nebius LLM call failed: {e}") from e

    async def chat_json_object(
        self,
        messages: List[Dict[str, str]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        if not self._client:
            raise upstream_error("NEBIUS_API_KEY is not set; LLM call is disabled")

        try:
            resp = await self._client.chat.completions.create(
                model=model or settings.nebius_model,
                messages=messages,
                temperature=temperature if temperature is not None else settings.llm_temperature,
                max_tokens=max_tokens or settings.llm_max_tokens,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            raise upstream_error(f"Nebius LLM call failed: {e}") from e