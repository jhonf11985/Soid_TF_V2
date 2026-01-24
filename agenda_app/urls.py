from django.urls import path
from . import views

app_name = "agenda_app"

urlpatterns = [
    path("", views.home, name="home"),
    path("anual/", views.agenda_anual, name="agenda_anual"),

    path("actividad/nueva/", views.actividad_create, name="actividad_create"),
    path("actividad/<int:pk>/", views.actividad_detail, name="actividad_detail"),
    path("actividad/<int:pk>/editar/", views.actividad_update, name="actividad_update"),
    path("actividad/<int:pk>/eliminar/", views.actividad_delete, name="actividad_delete"),
]
