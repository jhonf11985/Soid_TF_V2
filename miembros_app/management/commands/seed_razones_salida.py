from django.core.management.base import BaseCommand
from django.db import transaction

from miembros_app.models import RazonSalidaMiembro


class Command(BaseCommand):
    help = "Seed de razones de salida separadas para Miembros y Nuevos Creyentes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-orden",
            action="store_true",
            help="Reasigna el orden según el seed recomendado.",
        )
        parser.add_argument(
            "--desactivar-no-incluidas",
            action="store_true",
            help="Desactiva razones existentes que no estén en el seed.",
        )

    @transaction.atomic
    def handle(self, *args, **options):

        # =========================
        # RAZONES – NUEVO CREYENTE
        # (solo las propias de seguimiento/contacto + algunas generales)
        # =========================
        razones_nuevo_creyente = [
            ("No se logró establecer contacto", "No fue posible contactar al nuevo creyente.", "nuevo_creyente"),
            ("Datos de contacto incorrectos", "Los datos registrados no permitieron contacto.", "nuevo_creyente"),
            ("No se le dio seguimiento", "No se realizó el seguimiento pastoral a tiempo.", "nuevo_creyente"),
            ("Seguimiento incompleto", "El seguimiento se inició pero no se completó.", "nuevo_creyente"),
            ("Abandonó el proceso de seguimiento", "Inició el proceso pero no continuó.", "nuevo_creyente"),

            # Generales (aplican a ambos)
            ("Descarriado", "Se apartó y dejó de congregarse.", "ambos"),
            ("Dejó de congregarse", "Dejó de asistir de forma sostenida.", "ambos"),
            ("Se trasladó a otra iglesia", "Se congrega actualmente en otra iglesia.", "ambos"),
            ("Cambio de residencia", "Mudanza a otra ciudad o país.", "ambos"),
            ("Cambio de horario laboral", "El horario laboral impidió continuar asistiendo.", "ambos"),
            ("Salud", "Situación de salud limitó la asistencia.", "ambos"),
            ("Fallecimiento", "Registro histórico por fallecimiento.", "ambos"),
            ("Problemas personales", "Situación personal afectó la continuidad.", "ambos"),
            ("Situación familiar", "Situación familiar afectó la continuidad.", "ambos"),
        ]

        # =========================
        # RAZONES – MIEMBRO
        # (solo las propias de miembro oficial + generales)
        # =========================
        razones_miembro = [
            ("Renuncia voluntaria", "Decisión personal de dejar la membresía.", "miembro"),
            ("Disciplina", "Salida relacionada a un proceso disciplinario.", "miembro"),

            # Generales (aplican a ambos)
            ("Descarriado", "Se apartó y dejó de congregarse.", "ambos"),
            ("Dejó de congregarse", "Dejó de asistir de forma sostenida.", "ambos"),
            ("Se trasladó a otra iglesia", "Se congrega actualmente en otra iglesia.", "ambos"),
            ("Cambio de residencia", "Mudanza a otra ciudad o país.", "ambos"),
            ("Cambio de horario laboral", "El horario laboral impidió continuar asistiendo.", "ambos"),
            ("Salud", "Situación de salud limitó la asistencia.", "ambos"),
            ("Fallecimiento", "Registro histórico por fallecimiento.", "ambos"),
            ("Problemas personales", "Situación personal afectó la continuidad.", "ambos"),
            ("Situación familiar", "Situación familiar afectó la continuidad.", "ambos"),
        ]

        # Unimos y quitamos duplicados por nombre, dejando la última ocurrencia (misma aplica_a/desc)
        # (Así “Descarriado”/etc no se crean dos veces)
        merged = {}
        orden_lista = []

        for nombre, desc, aplica_a in (razones_nuevo_creyente + razones_miembro):
            merged[nombre] = (desc, aplica_a)
            if nombre not in orden_lista:
                orden_lista.append(nombre)

        razones_final = [(n, merged[n][0], merged[n][1]) for n in orden_lista]

        reset_orden = options["reset_orden"]
        desactivar_no_incluidas = options["desactivar_no_incluidas"]

        nombres_seed = []
        creadas = 0
        actualizadas = 0

        for orden, (nombre, descripcion, aplica_a) in enumerate(razones_final, start=1):
            nombres_seed.append(nombre)

            obj, created = RazonSalidaMiembro.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "descripcion": descripcion,
                    "activo": True,
                    "orden": orden,
                    "aplica_a": aplica_a,
                },
            )

            if created:
                creadas += 1
            else:
                cambios = False

                if (obj.descripcion or "") != (descripcion or ""):
                    obj.descripcion = descripcion
                    cambios = True

                if obj.aplica_a != aplica_a:
                    obj.aplica_a = aplica_a
                    cambios = True

                if obj.activo is False:
                    obj.activo = True
                    cambios = True

                if reset_orden and obj.orden != orden:
                    obj.orden = orden
                    cambios = True

                if cambios:
                    obj.save()
                    actualizadas += 1

        desactivadas = 0
        if desactivar_no_incluidas:
            qs = RazonSalidaMiembro.objects.exclude(nombre__in=nombres_seed).filter(activo=True)
            desactivadas = qs.update(activo=False)

        self.stdout.write(self.style.SUCCESS("✅ Seed de razones de salida completado"))
        self.stdout.write(f" - Creadas: {creadas}")
        self.stdout.write(f" - Actualizadas: {actualizadas}")
        if desactivar_no_incluidas:
            self.stdout.write(f" - Desactivadas (no incluidas): {desactivadas}")