import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from miembros_app.models import (
    Miembro,
    MiembroRelacion,
    sync_familia_inteligente_por_relacion,
)

# =========================
# DATOS BASE
# =========================

NOMBRES_M = [
    "Juan", "Pedro", "Luis", "Carlos", "José", "Miguel", "Rafael",
    "Andrés", "Daniel", "Manuel", "Kelvin", "Jairo", "Alex",
    "Jahir", "Jonah", "Samuel", "Emanuel", "Wilmer"
]

NOMBRES_F = [
    "María", "Ana", "Carmen", "Luisa", "Patricia", "Rosa", "Yolanda",
    "Claudia", "Laura", "Andrea", "Dariany", "Dariane",
    "Julieth", "Jaressi", "Yede", "Yeliany", "Paola"
]

APELLIDOS = [
    "Pérez", "García", "Rodríguez", "Martínez", "Hernández",
    "Gómez", "Díaz", "Ramírez", "Sánchez", "Castillo",
    "Melo", "Guerrero", "Del Rosario", "De la Cruz", "Santana"
]

SECTORES = [
    "21 de Enero", "30 de Mayo", "Ana Melia", "Anamuya", "Antonio Guzmán",
    "Brisas del Duey", "Cristo Rey", "Don Celso", "Duarte", "Juan Pablo Duarte",
    "El Bonao", "El Centro", "El Chorro", "El Macao", "El Obispado",
    "El Tamarindo", "La Altagracia", "La Aviación", "La Cabrera", "La Candelaria",
    "La Ceiba del Salado", "La Colonia", "La Cruz", "La Fe", "La Laguna",
    "La Malena", "La Mina", "La Otra Banda", "Las Caobas", "Las Flores",
    "Las Mercedes", "Los Platanitos", "Los Ríos", "Los Sotos", "Luisa Perla",
    "Mamá Tingó", "Nazaret", "San Francisco", "San José", "San Martín",
    "San Pedro", "Santa Cruz", "Santana", "Savica", "Villa Cerro",
    "Villa Hortensia", "Villa María", "Villa Palmera", "Villa Progreso", "Yuma",
]

CIUDAD_FIJA = "Higuey"
PROVINCIA_FIJA = "La Altagracia"

ESTADOS_MIEMBRO = ["activo", "pasivo", "observacion"]

ESTADOS_CIVIL_FORM = [
    "Soltero/a",
    "Casado/a",
    "Divorciado/a",
    "Viudo/a",
    "Unión libre",
]


def telefono_rd():
    return random.choice(["809", "829", "849"]) + str(random.randint(1000000, 9999999))


class Command(BaseCommand):
    help = "Carga miembros de prueba con estado civil visible + relaciones familiares (hogares y clanes)."

    def add_arguments(self, parser):
        parser.add_argument("--total", type=int, default=100, help="Cantidad de miembros a crear")

    def handle(self, *args, **options):
        total = options["total"]
        miembros = []

        # =========================
        # 1️⃣ Crear miembros base
        # =========================
        for _ in range(total):
            genero = random.choice(["masculino", "femenino"])
            nombre = random.choice(NOMBRES_M if genero == "masculino" else NOMBRES_F)
            apellido = random.choice(APELLIDOS)

            edad = random.randint(5, 75)
            fecha_nacimiento = date.today() - timedelta(days=edad * 365)

            tel = telefono_rd()

            miembro = Miembro.objects.create(
                nombres=nombre,
                apellidos=apellido,
                genero=genero,
                fecha_nacimiento=fecha_nacimiento,
                telefono=tel,
                whatsapp=tel,
                email=f"{nombre.lower()}.{apellido.lower()}{random.randint(1,999)}@correo.com",

                sector=random.choice(SECTORES),
                ciudad=CIUDAD_FIJA,
                provincia=PROVINCIA_FIJA,

                estado_miembro=random.choice(ESTADOS_MIEMBRO),
                estado_civil="Soltero/a",  # 👈 compatible con el Form
                activo=True,
                nuevo_creyente=(random.random() < 0.15),
                bautizado_confirmado=(random.random() < 0.7),
            )

            miembros.append(miembro)

        # =========================
        # 2️⃣ Crear parejas (Casado/a)
        # =========================
        adultos = [m for m in miembros if m.edad and m.edad >= 18]
        random.shuffle(adultos)

        cantidad_parejas = int(len(adultos) * 0.30) // 2
        parejas_creadas = 0

        for i in range(cantidad_parejas):
            m1 = adultos[i * 2]
            m2 = adultos[i * 2 + 1]

            if m1.genero == m2.genero:
                continue

            with transaction.atomic():
                m1.estado_civil = "Casado/a"
                m2.estado_civil = "Casado/a"
                m1.save(update_fields=["estado_civil"])
                m2.save(update_fields=["estado_civil"])

                rel1 = MiembroRelacion.objects.create(
                    miembro=m1,
                    familiar=m2,
                    tipo_relacion="conyuge",
                    es_inferida=True,
                )
                MiembroRelacion.objects.create(
                    miembro=m2,
                    familiar=m1,
                    tipo_relacion="conyuge",
                    es_inferida=True,
                )

                sync_familia_inteligente_por_relacion(rel1)
                parejas_creadas += 1

        # =========================
        # 3️⃣ Crear hijos
        # =========================
        casados = list(Miembro.objects.filter(estado_civil="Casado/a"))
        random.shuffle(casados)

        padres_a_usar = casados[: int(len(casados) * 0.40)]
        hijos_creados = 0

        for padre in padres_a_usar:
            for _ in range(random.randint(1, 3)):
                genero = random.choice(["masculino", "femenino"])
                nombre = random.choice(NOMBRES_M if genero == "masculino" else NOMBRES_F)

                edad_hijo = random.randint(1, 17)
                fecha_nacimiento = date.today() - timedelta(days=edad_hijo * 365)

                hijo = Miembro.objects.create(
                    nombres=nombre,
                    apellidos=padre.apellidos,
                    genero=genero,
                    fecha_nacimiento=fecha_nacimiento,
                    estado_miembro="activo",
                    activo=True,
                    estado_civil="Soltero/a",
                )

                rel = MiembroRelacion.objects.create(
                    miembro=padre,
                    familiar=hijo,
                    tipo_relacion="hijo",
                    es_inferida=True,
                )

                sync_familia_inteligente_por_relacion(rel)
                hijos_creados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Miembros: {len(miembros)} | Parejas: {parejas_creadas} | Hijos: {hijos_creados}"
            )
        )
