# notificaciones_app/management/commands/limpiar_suscripciones_viejas.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from notificaciones_app.models import PushSubscription


class Command(BaseCommand):
    help = "Desactiva suscripciones push que no se han actualizado en X días"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dias",
            type=int,
            default=7,
            help="Días sin actualización para considerar una suscripción como inactiva (default: 7)",
        )
        parser.add_argument(
            "--eliminar",
            action="store_true",
            help="Eliminar las suscripciones en lugar de solo desactivarlas",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo mostrar qué se haría, sin ejecutar cambios",
        )

    def handle(self, *args, **options):
        dias = options["dias"]
        eliminar = options["eliminar"]
        dry_run = options["dry_run"]

        fecha_limite = timezone.now() - timedelta(days=dias)

        # Buscar suscripciones activas que no se han actualizado
        suscripciones_viejas = PushSubscription.objects.filter(
            activo=True,
            actualizado_en__lt=fecha_limite,
        )

        total = suscripciones_viejas.count()

        if total == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ No hay suscripciones activas sin actualizar en los últimos {dias} días."
                )
            )
            return

        self.stdout.write(
            f"📋 Encontradas {total} suscripciones sin actualizar en {dias}+ días:"
        )

        for sub in suscripciones_viejas[:10]:  # Mostrar solo las primeras 10
            self.stdout.write(
                f"   - Usuario: {sub.user} | Última actualización: {sub.actualizado_en}"
            )

        if total > 10:
            self.stdout.write(f"   ... y {total - 10} más")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"\n🔍 DRY RUN: No se realizaron cambios.")
            )
            return

        if eliminar:
            suscripciones_viejas.delete()
            self.stdout.write(
                self.style.SUCCESS(f"\n🗑️  Eliminadas {total} suscripciones viejas.")
            )
        else:
            suscripciones_viejas.update(activo=False)
            self.stdout.write(
                self.style.SUCCESS(f"\n🔕 Desactivadas {total} suscripciones viejas.")
            )