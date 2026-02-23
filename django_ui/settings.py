# /django_ui/settings.py
# This is the settings module for the Django UI of the Repo Summarizer application. It defines the 
# configuration for the Django project, including installed apps, middleware, templates, and static files.
import os

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret")
DEBUG = False
ALLOWED_HOSTS = ["*"]

ROOT_URLCONF = "django_ui.urls"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

STATIC_URL = "/static/"