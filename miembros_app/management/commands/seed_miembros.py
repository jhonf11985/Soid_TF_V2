import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from miembros_app.models import Miembro


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

# ✅ SECTORES (VALORES EXACTOS DEL <select> DE miembro_form.html)
SECTORES = [
    "21 de Enero",
    "30 de Mayo",
    "Ana Melia",
    "Anamuya",
    "Antonio Guzmán",
    "Brisas del Duey",
    "Cristo Rey",
    "Don Celso",
    "Duarte",
    "Juan Pablo Duarte",
    "El Bonao",
    "El Centro",
    "El Chorro",
    "El Macao",
    "El Obispado",
    "El Tamarindo",
    "La Altagracia",
    "La Aviación",
    "La Cabrera",
    "La Candelaria",
    "La Ceiba del Salado",
    "La Colonia",
    "La Cruz",
    "La Fe",
    "La Laguna",
    "La Malena",
    "La Mina",
    "La Otra Banda",
    "Las Caobas",
    "Las Flores",
    "Las Mercedes",
    "Los Platanitos",
    "Los Ríos",
    "Los Sotos",
    "Luisa Perla",
    "Mamá Tingó",
    "Nazaret",
    "San Francisco",
    "San José",
    "San Martín",
    "San Pedro",
    "Santa Cruz",
    "Santana",
    "Savica",
    "Villa Cerro",
    "Villa Hortensia",
    "Villa María",
    "Villa Palmera",
    "Villa Progreso",
    "Yuma",
]

# ✅ VALORES INTERNOS (SIN TILDE) PARA QUE EL SELECT LOS RECONOZCA
CIUDAD_FIJA = "Higuey"
PROVINCIA_FIJA = "La Altagracia"

ESTADOS_MIEMBRO = ["activo", "pasivo", "observacion"]


def telefono_rd():
    """Genera teléfono RD válido (10 dígitos)."""
    return random.choice(["809", "829", "849"]) + str(random.randint(1000000, 9999999))


class Command(BaseCommand):
    help = "Carga masiva de miembros de prueba (sector + ciudad/provincia fijas)"

    def add_arguments(self, parser):
        parser.add_argument("--total", type=int, default=200, help="Cantidad de miembros a crear")

    def handle(self, *args, **options):
        total = options["total"]
        creados = 0

        for _ in range(total):
            genero = random.choice(["masculino", "femenino"])
            nombre = random.choice(NOMBRES_M if genero == "masculino" else NOMBRES_F)
            apellido = random.choice(APELLIDOS)

            # Fecha nacimiento realista
            edad = random.randint(5, 75)
            fecha_nacimiento = date.today() - timedelta(days=edad * 365)

            tel = telefono_rd()

            miembro = Miembro(
                nombres=nombre,
                apellidos=apellido,
                genero=genero,
                fecha_nacimiento=fecha_nacimiento,
                telefono=tel,
                whatsapp=tel,
                email=f"{nombre.lower()}.{apellido.lower()}{random.randint(1,999)}@correo.com",

                # 📍 UBICACIÓN (CONTROLADA)
                sector=random.choice(SECTORES),
                ciudad=CIUDAD_FIJA,
                provincia=PROVINCIA_FIJA,

                estado_miembro=random.choice(ESTADOS_MIEMBRO),
                activo=True,
                nuevo_creyente=(random.random() < 0.15),
                bautizado_confirmado=(random.random() < 0.7),
            )

            miembro.save()
            creados += 1

        self.stdout.write(self.style.SUCCESS(f"✅ {creados} miembros de prueba creados correctamente."))
