from django.urls import path
from visitas_app.views import visita_list, visita_create

app_name = "visitas_app"

urlpatterns = [
    path("", visita_list, name="visita_list"),
    path("nueva/", visita_create, name="visita_create"),
]