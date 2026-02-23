# /api/routes.py
# This module defines the main API router for the Repo Summarizer application, which includes all the 
# individual endpoint routers.
from fastapi import APIRouter
from ..api.summarize import router as summarize_router

router = APIRouter()
router.include_router(summarize_router)