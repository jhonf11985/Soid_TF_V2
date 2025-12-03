from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('miembros_app', '0010_miembro_codigo_miembro_miembro_numero_miembro'),
    ]

    operations = [
        # Esta migración ya no hace nada porque el modelo final
        # ya está alineado con lo que queremos en 0010 + models.py
    ]
