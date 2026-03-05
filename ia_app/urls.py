# ia_app/urls.py
from django.urls import path
from .views import nl_query

app_name = "ia_app"

urlpatterns = [
    path("nl-query/", nl_query, name="nl_query"),
]