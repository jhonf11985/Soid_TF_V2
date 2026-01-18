# miembros_app/management/commands/enviar_notificaciones_cumpleanos.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from miembros_app.models import Miembro
from notificaciones_app.models import PushSubscription
from notificaciones_app.utils import enviar_push_notification


class Command(BaseCommand):
    help = 'Envía notificaciones de cumpleaños a todos los usuarios'

    def handle(self, *args, **options):
        hoy = timezone.now().date()
        
        # Buscar miembros que cumplen años hoy (solo activos)
        cumpleaneros = Miembro.objects.filter(
            fecha_nacimiento__month=hoy.month,
            fecha_nacimiento__day=hoy.day,
            activo=True  # Cambiado de estado='activo' a activo=True
        ).select_related('persona')
        
        if not cumpleaneros.exists():
            self.stdout.write(self.style.SUCCESS('No hay cumpleaños hoy'))
            return
        
        # Obtener todas las suscripciones activas
        suscripciones = PushSubscription.objects.filter(activo=True)
        
        if not suscripciones.exists():
            self.stdout.write(self.style.WARNING('No hay dispositivos registrados'))
            return
        
        # Preparar mensaje
        if cumpleaneros.count() == 1:
            cumpleanero = cumpleaneros.first()
            # Usar nombres y apellidos directamente del modelo Miembro
            nombre = f"{cumpleanero.nombres} {cumpleanero.apellidos}"
            titulo = "🎂 ¡Cumpleaños!"
            mensaje = f"Hoy es el cumpleaños de {nombre}. ¡Felicítalo!"
        else:
            nombres = [f"{c.nombres} {c.apellidos}" for c in cumpleaneros]
            titulo = f"🎂 ¡{cumpleaneros.count()} Cumpleaños Hoy!"
            mensaje = f"Cumpleaños: {', '.join(nombres)}"
        
        # Enviar notificación a todos los dispositivos
        enviadas = 0
        errores = 0
        
        for suscripcion in suscripciones:
            try:
                exito = enviar_push_notification(
                    suscripcion,
                    titulo,
                    mensaje,
                    url="/members/"
                )
                if exito:
                    enviadas += 1
                else:
                    errores += 1
            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(f'Error enviando a {suscripcion.id}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Notificaciones de cumpleaños enviadas: {enviadas}, Errores: {errores}'
            )
        )