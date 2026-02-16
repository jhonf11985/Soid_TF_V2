from django.db import migrations

def seed_casillas_f001(apps, schema_editor):
    CasillaF001 = apps.get_model("finanzas_app", "CasillaF001")

    casillas = [
        # INGRESOS IGLESIA
        ("ING_DIEZMOS", "Diezmos", "ingresos_iglesia", 10),
        ("ING_OFRENDA_VOL", "Ofrendas Voluntarias", "ingresos_iglesia", 20),
        ("ING_OFRENDA_ESP", "Ofrendas Especiales", "ingresos_iglesia", 30),
        ("ING_OTRAS_OFR", "Otras Ofrendas", "ingresos_iglesia", 40),
        ("ING_OTROS", "Otros Ingresos", "ingresos_iglesia", 50),
        ("ING_AYUDA_CONCILIO", "Ayudas del Concilio", "ingresos_iglesia", 60),
        ("ING_EXTERIOR", "Ofrendas del Exterior", "ingresos_iglesia", 70),

        # INGRESOS MINISTERIOS
        ("MIN_FEMENIL", "Ministerio Femenil", "ingresos_ministerios", 10),
        ("MIN_HOMBRES", "Hombres de Honor", "ingresos_ministerios", 20),
        ("MIN_EMBAJADORES", "Embajadores", "ingresos_ministerios", 30),
        ("MIN_ESC_BIBLICA", "Escuela Bíblica", "ingresos_ministerios", 40),
        ("MIN_MISIONERITAS", "Misioneritas", "ingresos_ministerios", 50),
        ("MIN_EXPLORADORES", "Exploradores", "ingresos_ministerios", 60),
        ("MIN_MDA", "MDA", "ingresos_ministerios", 70),
        ("MIN_MISIONES", "Misiones", "ingresos_ministerios", 80),
        ("MIN_OTROS", "Otros Ministerios", "ingresos_ministerios", 90),

        # EGRESOS
        ("EGR_ASIG_PASTORAL", "Asignación Pastoral", "egresos", 10),
        ("EGR_ALQUILER", "Alquileres Casa/Templo", "egresos", 20),
        ("EGR_EVANGELISMO", "Evangelismo y Misiones", "egresos", 30),
        ("EGR_SERVICIOS", "Agua, Luz, Teléfono", "egresos", 40),
        ("EGR_CAPILLAS", "Ayuda a Capillas", "egresos", 50),
        ("EGR_NECESITADOS", "Ayuda a Necesitados", "egresos", 60),
        ("EGR_MANTENIMIENTO", "Mantenimientos Varios", "egresos", 70),
        ("EGR_APOYO_MIN", "Apoyo a Minist. Locales", "egresos", 80),
        ("EGR_OTRAS", "Otras Salidas", "egresos", 90),
    ]

    for codigo, nombre, seccion, orden in casillas:
        CasillaF001.objects.update_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "seccion": seccion,
                "orden": orden,
                "activo": True,
            }
        )


class Migration(migrations.Migration):

    dependencies = [
        ("finanzas_app", "0014_casillaf001_categoriamovimiento_codigo_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_casillas_f001, migrations.RunPython.noop),
    ]
