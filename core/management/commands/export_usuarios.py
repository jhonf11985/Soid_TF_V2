from django.core.management.base import BaseCommand
from django.core import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from pathlib import Path
import json

class Command(BaseCommand):
    help = "Exporta usuarios + grupos + permisos a JSON (para restaurar después de resetear BD)."

    def handle(self, *args, **options):
        data = []

        User = get_user_model()

        # Grupos
        groups = Group.objects.all()
        data.extend(json.loads(serializers.serialize("json", groups)))

        # Permisos (útil si tienes permisos personalizados)
        perms = Permission.objects.all()
        data.extend(json.loads(serializers.serialize("json", perms)))

        # Usuarios
        users = User.objects.all()
        data.extend(json.loads(serializers.serialize("json", users)))

        output_file = Path("usuarios_y_roles.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(
            f"✅ Usuarios/roles exportados correctamente a: {output_file}"
        ))
