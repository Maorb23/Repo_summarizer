# /api/schemas.py
# This module defines the request and response schemas for the Repo Summarizer API, as well as a 
# standard error response format.
from pydantic import BaseModel, HttpUrl, Field
from typing import List


class SummarizeRequest(BaseModel):
    github_url: HttpUrl = Field(..., description="URL of a public GitHub repository")


class SummarizeResponse(BaseModel):
    summary: str
    technologies: List[str]
    structure: str


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str