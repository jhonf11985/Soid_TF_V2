from django.db import migrations, models


def poblar_telefono_norm(apps, schema_editor):
    import re
    Miembro = apps.get_model("miembros_app", "Miembro")
    
    for m in Miembro.objects.all():
        if m.telefono:
            digits = re.sub(r"\D+", "", m.telefono)
            # Si tiene 11 dígitos y empieza con 1, quitar el 1
            if len(digits) == 11 and digits.startswith("1"):
                digits = digits[1:]
            m.telefono_norm = digits[:10] if digits else None
        else:
            m.telefono_norm = None
        m.save(update_fields=["telefono_norm"])


class Migration(migrations.Migration):

    dependencies = [
        ('miembros_app', '0026_miembrobitacora'),
    ]

    operations = [
        migrations.AddField(
            model_name='miembro',
            name='telefono_norm',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=10,
            ),
        ),
        migrations.RunPython(poblar_telefono_norm, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name='miembro',
            index=models.Index(fields=['telefono_norm'], name='miembros_te_norm_idx'),
        ),
    ]