from django.apps import AppConfig




class NotificacionesAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notificaciones_app'

    def ready(self):
        # Importar signals para que se registren
        import notificaciones_app.signals  # noqa: F401