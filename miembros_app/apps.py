from django.apps import AppConfig


class MiembrosAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'miembros_app'

    def ready(self):
        import miembros_app.signals  # ← Agregar esta línea