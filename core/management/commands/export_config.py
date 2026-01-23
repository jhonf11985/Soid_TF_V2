from django.core.management.base import BaseCommand
from django.core import serializers
from core.models import Module, ConfiguracionSistema
from pathlib import Path
import json


class Command(BaseCommand):
    help = "Exporta la configuración global del sistema (módulos + configuración)"

    def handle(self, *args, **options):
        data = []

        # Exportar módulos
        modules = Module.objects.all()
        modules_json = serializers.serialize("json", modules)
        data.extend(json.loads(modules_json))

        # Exportar configuración global (singleton)
        config = ConfiguracionSistema.objects.all()
        config_json = serializers.serialize("json", config)
        data.extend(json.loads(config_json))

        # Guardar archivo
        output_file = Path("config_global_modulos.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(
            f"✅ Configuración exportada correctamente a: {output_file}"
        ))
