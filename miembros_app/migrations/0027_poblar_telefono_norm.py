from django.db import migrations
import re

def digits_only(v: str) -> str:
    return re.sub(r"\D+", "", (v or ""))

def norm_rd_phone(v: str) -> str:
    d = digits_only(v)
    if len(d) == 11 and d.startswith("1"):
        d = d[1:]
    if len(d) > 10:
        d = d[:10]
    return d

def forward(apps, schema_editor):
    Miembro = apps.get_model("miembros_app", "Miembro")

    # Rellenar telefono_norm
    for m in Miembro.objects.all():


        tel_norm = norm_rd_phone(m.telefono)

        # si está vacío, lo dejamos vacío
        if not tel_norm:
            if m.telefono_norm != "":
                m.telefono_norm = ""
                m.save(update_fields=["telefono_norm"])
            continue

        # Solo asigna si cambió
        if m.telefono_norm != tel_norm:
            m.telefono_norm = tel_norm
            m.save(update_fields=["telefono_norm"])

def backward(apps, schema_editor):
    Miembro = apps.get_model("miembros_app", "Miembro")
    Miembro.objects.update(telefono_norm="")

class Migration(migrations.Migration):

    dependencies = [
        # ⚠️ pon aquí la migración anterior a esta
        # Ejemplo: ("miembros_app", "00XX_add_telefono_norm"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
