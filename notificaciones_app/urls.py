from django.urls import path
from . import views
from . import views_push  
from .views_cron import cron_motor  
app_name = "notificaciones_app"

urlpatterns = [
    path("marcar-leidas/", views.marcar_todas_leidas, name="marcar_todas_leidas"),
        path("push/status/", views_push.push_status, name="push_status"),
    path("push/subscribe/", views_push.push_subscribe, name="push_subscribe"),
    path("push/unsubscribe/", views_push.push_unsubscribe, name="push_unsubscribe"),

    path("push/test/", views_push.push_test, name="push_test"),
       path("cron/motor/", cron_motor, name="cron_motor"),

]
