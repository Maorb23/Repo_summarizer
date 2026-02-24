# /django_ui/asgi.py
# This module sets up the ASGI application for the Django UI of the Repo Summarizer application. It configures the environment and 
# initializes Django to create the ASGI application that can be served by an ASGI server 
# like Daphne or Uvicorn.
import os
import django
from django.core.asgi import get_asgi_application

def get_django_asgi_app():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_ui.settings")
    django.setup(set_prefix=False)
    return get_asgi_application()