from django.urls import path
from . import views

app_name = "agenda_app"

urlpatterns = [
    path("", views.home, name="home"),
]
