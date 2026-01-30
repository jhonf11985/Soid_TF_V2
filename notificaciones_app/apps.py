from django.apps import AppConfig

class NotificacionesAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notificaciones_app"

    def ready(self):
        import notificaciones_app.signals  # <-- Agregar esta línea
        from notificaciones_app.motor import registrar_task
        from agenda_app.cron import task_recordatorios_agenda

        registrar_task("agenda_recordatorios", task_recordatorios_agenda)
