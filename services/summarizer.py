# /services/summarizer.py
# This module defines the RepoSummarizer class, which uses the NebiusLLMClient to generate a summary of 
# a GitHub repository based on a structured prompt that includes selected file contents and repository metadata.
from __future__ import annotations

import json
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from ..services.llm_client import NebiusLLMClient
from ..services.repo_processor import RepoContext, SelectedFile
from ..utils.text import truncate


class LlmSummary(BaseModel):
    summary: str = Field(..., description="Human-readable markdown summary of the repository")
    technologies: List[str] = Field(..., description="Main languages/frameworks/libraries used")
    structure: str = Field(..., description="Brief description of project structure and directories")


class RepoSummarizer:
    def __init__(self, llm: NebiusLLMClient) -> None:
        self.llm = llm

    def _build_prompt(self, ctx: RepoContext) -> List[Dict[str, str]]:
        files_block = []
        for f in ctx.selected_files:
            files_block.append(
                f"## {f.path}  ({f.reason})\n"
                f"{f.content}\n"
            )

        user_payload = (
            f"Repository: {ctx.full_name}\n"
            f"Description: {ctx.description or '(none)'}\n"
            f"Default branch: {ctx.default_branch}\n"
            f"Homepage: {ctx.homepage or '(none)'}\n"
            f"Topics: {', '.join(ctx.topics) if ctx.topics else '(none)'}\n"
            f"GitHub languages(bytes): {ctx.languages}\n"
            f"Extracted tech hints: {ctx.extracted_tech}\n"
            f"{ctx.structure_hint}\n\n"
            "### Files (snippets)\n"
            + "\n".join(files_block)
        )

        # keep user payload bounded as an extra safety net
        user_payload = truncate(user_payload, 55_000)

        system = (
            "You are a senior software engineer. Summarize the GitHub repository using ONLY the provided data.\n"
            "Return STRICT JSON with keys: summary, technologies, structure.\n"
            "- summary: 4-8 sentences in markdown, mention what it does and primary use-cases.\n"
            "- technologies: 5-15 concise strings (languages, frameworks, major libs, tooling). No versions.\n"
            "- structure: 2-4 sentences describing directory layout and key files.\n"
            "If something is unknown, say so briefly (do not hallucinate).\n"
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_payload},
        ]

    async def summarize(self, ctx: RepoContext) -> Dict[str, Any]:
        messages = self._build_prompt(ctx)
        schema = LlmSummary.model_json_schema()

        # Prefer strict json_schema mode; fall back to json_object if needed.
        raw = await self.llm.chat_json_schema(messages=messages, json_schema=schema)

        try:
            data = json.loads(raw)
            parsed = LlmSummary(**data)
        except Exception:
            raw2 = await self.llm.chat_json_object(messages=messages)
            data2 = json.loads(raw2)
            parsed = LlmSummary(**data2)

        # normalize technologies
        tech = []
        seen = set()
        for t in parsed.technologies:
            t2 = (t or "").strip()
            if not t2:
                continue
            key = t2.lower()
            if key not in seen:
                seen.add(key)
                tech.append(t2)
        parsed.technologies = tech[:15]

        return parsed.model_dump()