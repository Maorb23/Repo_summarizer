# /django_ui/views.py
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from utils.errors import AppError

# Populated by main.py at startup
_svc = None

async def index(request):
    context = {}

    if request.method == "POST":
        github_url = request.POST.get("github_url", "").strip()
        context["github_url"] = github_url
        if not github_url:
            context["error"] = "Please enter a GitHub URL."
        elif _svc is None:
            context["error"] = "Summarizer service is not available."
        else:
            try:
                result = await _svc.summarize_repo(github_url)
                context["result"] = result
            except AppError as e:
                context["error"] = e.message
            except Exception as e:
                context["error"] = f"Unexpected error: {e}"

    return render(request, "django_ui/index.html", context)