from django.urls import path
from . import views

app_name = "agenda_app"

urlpatterns = [
    path("", views.home, name="home"),
    path("anual/", views.agenda_anual, name="agenda_anual"),

    # Crear actividad
    path("nueva/", views.actividad_create, name="actividad_create"),
]
