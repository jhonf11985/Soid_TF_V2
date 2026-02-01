from django.urls import path
from . import views

app_name = "codigo_qr"

urlpatterns = [
    path("scan/", views.qr_scan, name="scan"),
    path("t/<str:token>/", views.qr_resolver, name="resolver"),
    path("img/<str:token>/", views.qr_imagen, name="imagen"),
    path("miembro/<int:miembro_id>/", views.qr_por_miembro, name="por_miembro"),

    # Envíos en lote
    path("envios/", views.envios_home, name="envios_home"),
    path("envios/crear/", views.envios_crear_lote, name="envios_crear_lote"),
    path("envios/pendientes/", views.envios_pendientes, name="envios_pendientes"),
    path("envios/enviar/<int:envio_id>/", views.envios_enviar, name="envios_enviar"),
    path("envios/marcar-enviado/<int:envio_id>/", views.envios_marcar_enviado, name="envios_marcar_enviado"),
    path("enviar-desde-detalle/<str:token>/", views.envio_desde_detalle, name="envio_desde_detalle"),

]