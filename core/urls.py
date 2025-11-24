from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # Página de inicio del sistema
    path("", views.home, name="home"),
]
