from django.urls import path
from . import views

app_name = "nuevo_creyente_app"

urlpatterns = [
    path("", views.dashboard, name="nuevo_creyente"),
]
