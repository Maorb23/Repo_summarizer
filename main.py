# /main.py
# This is the main entry point for the Repo Summarizer application. It sets up the FastAPI app, including configuration, routes, services, and error handling.
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from settings import settings
from utils.errors import AppError
from api.routes import router
from services.github_client import GitHubClient
from services.llm_client import NebiusLLMClient
from services.summarize_service import SummarizeService
import api.summarize as summarize_mod

# Optional Django UI mount -- INTERACTIVE interface in local/ui for testing and demo purposes. Can be disabled in production or if Django setup is not desired.
def mount_django(app: FastAPI) -> None:
    if not settings.enable_django_ui:
        print("Django UI disabled (ENABLE_DJANGO_UI is False)")
        return
    try:
        from django_ui.asgi import get_django_asgi_app
        django_app = get_django_asgi_app()
        app.mount("/ui", django_app) ## GO to localhost:8000/ui to access the Django UI
        print("Django UI mounted at /ui")
    except Exception as e:
        print(f"Django UI failed to mount: {e}")
        import traceback; traceback.print_exc()


@asynccontextmanager # For FastAPI lifespan event, to initialize and cleanup resources like HTTP clients if needed.
async def lifespan(app: FastAPI):
    github = GitHubClient()
    llm = NebiusLLMClient()
    svc = SummarizeService(github=github, llm=llm)

    # expose service on app.state and patch dependency in summarize.py
    app.state.svc = svc
    
    summarize_mod.get_service = lambda: app.state.svc

    # inject service into Django UI
    if settings.enable_django_ui:
        try:
            import django_ui.views as django_views
            django_views._svc = svc
        except Exception:
            pass

    yield

    await github.aclose()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(router)
mount_django(app)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"status": "error", "message": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    # Force the required error shape
    return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid request body"})


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"status": "error", "message": "Internal server error"})