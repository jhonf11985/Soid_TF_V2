from django.core.management.base import BaseCommand
from miembros_app.models import ZonaGeo

ZONAS = [
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

CIUDAD = "Higüey"
PROVINCIA = "La Altagracia"


class Command(BaseCommand):
    help = "Seed de sectores de Higüey (ZonaGeo) sin lat/lng"

    def handle(self, *args, **options):
        creadas = 0
        existentes = 0

        for sector in ZONAS:
            obj, created = ZonaGeo.objects.get_or_create(
                sector=sector.strip(),
                ciudad=CIUDAD,
                provincia=PROVINCIA,
                defaults={
                    "lat": None,
                    "lng": None,
                }
            )

            if created:
                creadas += 1
            else:
                existentes += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Zonas creadas: {creadas}"))
        self.stdout.write(self.style.WARNING(f"ℹ️ Zonas ya existentes: {existentes}"))
        self.stdout.write(self.style.SUCCESS("Listo. Ahora completa lat/lng desde el admin → ZonaGeo."))
