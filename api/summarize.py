# /api/summarize.py
# This module defines the API endpoint for summarizing a GitHub repository. It uses FastAPI to
from fastapi import APIRouter, Depends
from api.schemas import SummarizeRequest, SummarizeResponse
from services.summarize_service import SummarizeService

router = APIRouter()


def get_service() -> SummarizeService:
    # injected in app.main via app.state; this is replaced at runtime
    raise RuntimeError("Service not initialized")


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_repo(payload: SummarizeRequest):
    svc: SummarizeService = get_service()  # patched in main.py
    return await svc.summarize_repo(str(payload.github_url))