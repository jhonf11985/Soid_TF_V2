# core/urls_docs.py

from django.urls import path
from .views_docs import ver_doc_publico

app_name = "docs"

urlpatterns = [
    path("<str:token>/", ver_doc_publico, name="ver"),
]
