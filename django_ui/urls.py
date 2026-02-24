from django.urls import path
from django_ui.views import index

urlpatterns = [
    path("", index),
]