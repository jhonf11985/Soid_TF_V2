from django.core.management.base import BaseCommand
from django.db import transaction
from miembros_app.models import RazonSalidaMiembro


class Command(BaseCommand):
    help = "Seed definitivo de razones de salida abreviadas (Desc. / Trasl.)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-orden",
            action="store_true",
            help="Reasigna el orden según el seed.",
        )
        parser.add_argument(
            "--desactivar-no-incluidas",
            action="store_true",
            help="Desactiva razones existentes que no estén en el seed.",
        )

    @transaction.atomic
    def handle(self, *args, **options):

        # Formato:
        # (nombre, descripcion, aplica_a, estado_resultante, permite_carta)
        razones = [
            # =========================
            # 🔴 DESC. POR… (AMBOS)
            # =========================
            ("Desc. por abandono voluntario", "Se apartó y dejó de congregarse de forma voluntaria.", "ambos", "descarriado", False),
            ("Desc. por problemas personales", "Se apartó por situaciones personales.", "ambos", "descarriado", False),
            ("Desc. por situación familiar", "Se apartó por situaciones familiares.", "ambos", "descarriado", False),
            ("Desc. por falta de compromiso", "Se apartó por falta de constancia o compromiso con la congregación.", "ambos", "descarriado", False),
            ("Desc. tras dejar de congregarse", "Dejó de asistir de forma sostenida y se considera descarriado.", "ambos", "descarriado", False),
            ("Desc. sin causa especificada", "No se documentó la causa del apartamiento.", "ambos", "descarriado", False),

            # =========================
            # 🔴 DESC. POR… (NUEVO CREYENTE)
            # =========================
            ("Desc. por falta de seguimiento", "No se realizó seguimiento pastoral y el proceso se perdió.", "nuevo_creyente", "descarriado", False),
            ("Desc. por seguimiento incompleto", "El seguimiento se inició pero no se completó.", "nuevo_creyente", "descarriado", False),
            ("Desc. por abandono del proceso", "Inició el proceso de seguimiento pero no continuó.", "nuevo_creyente", "descarriado", False),
            ("Desc. por pérdida de contacto", "Se perdió el contacto tras varios intentos.", "nuevo_creyente", "descarriado", False),
            ("Desc. por datos de contacto incorrectos", "Los datos registrados no permitieron mantener contacto.", "nuevo_creyente", "descarriado", False),
            ("Desc. por no se logró contacto", "No fue posible contactar al nuevo creyente desde el inicio.", "nuevo_creyente", "descarriado", False),

            # =========================
            # 🟢 TRASL. POR… (AMBOS)
            # =========================
            ("Trasl. por cambio de residencia", "Cambio de residencia con iglesia destino.", "ambos", "trasladado", True),
            ("Trasl. por integración a otra iglesia", "Se integra activamente a otra congregación.", "ambos", "trasladado", True),
            ("Trasl. por recomendación pastoral", "Traslado recomendado o avalado por liderazgo pastoral.", "ambos", "trasladado", True),
            ("Trasl. por motivos familiares", "Traslado motivado por contexto familiar.", "ambos", "trasladado", True),
            ("Trasl. por estudios o trabajo", "Traslado por estudios o razones laborales.", "ambos", "trasladado", True),
        ]

        reset_orden = options["reset_orden"]
        desactivar_no_incluidas = options["desactivar_no_incluidas"]

        nombres_seed = []
        creadas = 0
        actualizadas = 0

        for orden, (nombre, descripcion, aplica_a, estado, permite_carta) in enumerate(razones, start=1):
            nombres_seed.append(nombre)

            obj, created = RazonSalidaMiembro.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "descripcion": descripcion,
                    "activo": True,
                    "orden": orden,
                    "aplica_a": aplica_a,
                    "estado_resultante": estado,
                    "permite_carta": permite_carta,
                },
            )

            if created:
                creadas += 1
                continue

            cambios = False
            if obj.descripcion != descripcion:
                obj.descripcion = descripcion
                cambios = True
            if obj.aplica_a != aplica_a:
                obj.aplica_a = aplica_a
                cambios = True
            if obj.estado_resultante != estado:
                obj.estado_resultante = estado
                cambios = True
            if obj.permite_carta != permite_carta:
                obj.permite_carta = permite_carta
                cambios = True
            if reset_orden and obj.orden != orden:
                obj.orden = orden
                cambios = True
            if not obj.activo:
                obj.activo = True
                cambios = True

            if cambios:
                obj.save()
                actualizadas += 1

        if desactivar_no_incluidas:
            RazonSalidaMiembro.objects.exclude(nombre__in=nombres_seed).update(activo=False)

        self.stdout.write(self.style.SUCCESS("✅ Seed de razones de salida (abreviado) aplicado"))
        self.stdout.write(f" - Creadas: {creadas}")
        self.stdout.write(f" - Actualizadas: {actualizadas}")
        if desactivar_no_incluidas:
            self.stdout.write(self.style.WARNING(" - Razones no incluidas: desactivadas"))
