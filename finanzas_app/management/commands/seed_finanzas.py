from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Semilla oficial de Finanzas: resetea (opcional) y crea Casillas F001 + Categorías mapeadas + Cuentas base."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Borra TODO lo de finanzas (adjuntos, movimientos, categorías, casillas, cuentas) antes de sembrar.",
        )
        parser.add_argument(
            "--moneda",
            default="DOP",
            choices=["DOP", "USD", "EUR"],
            help="Moneda por defecto para las cuentas base (DOP por defecto).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset = options["reset"]
        moneda = options["moneda"]

        # Importamos modelos en caliente (así no explota si cambias nombres al mover cosas)
        from finanzas_app.models import CuentaFinanciera, CategoriaMovimiento, MovimientoFinanciero

        # Estos 2 existen en tu proyecto (ya los migraste). Si no, aquí fallaría y lo verías de inmediato.
        from finanzas_app.models import CasillaF001

        # Algunos proyectos tienen adjuntos; si no existe, lo ignoramos sin inventar.
        AdjuntoMovimiento = None
        try:
            from finanzas_app.models import AdjuntoMovimiento  # type: ignore
        except Exception:
            AdjuntoMovimiento = None

        if reset:
            self.stdout.write(self.style.WARNING("⚠️  RESET ACTIVADO: borrando TODO lo de finanzas..."))

            if AdjuntoMovimiento is not None:
                AdjuntoMovimiento.objects.all().delete()

            MovimientoFinanciero.objects.all().delete()
            CategoriaMovimiento.objects.all().delete()
            CasillaF001.objects.all().delete()
            CuentaFinanciera.objects.all().delete()

            self.stdout.write(self.style.SUCCESS("✔ Finanzas limpiado."))

        # ------------------------------------------------------------
        # 1) CASILLAS F001
        # ------------------------------------------------------------
        casillas = [
            # INGRESOS IGLESIA
            ("ING_DIEZMOS", "Diezmos", "ingresos_iglesia", 10),
            ("ING_OFRENDA_VOL", "Ofrendas Voluntarias", "ingresos_iglesia", 20),
            ("ING_OFRENDA_ESP", "Ofrendas Especiales", "ingresos_iglesia", 30),
            ("ING_OTRAS_OFR", "Otras Ofrendas", "ingresos_iglesia", 40),
            ("ING_OTROS", "Otros Ingresos", "ingresos_iglesia", 50),
            ("ING_AYUDA_CONCILIO", "Ayudas del Concilio", "ingresos_iglesia", 60),
            ("ING_EXTERIOR", "Ofrendas del Exterior", "ingresos_iglesia", 70),

            # INGRESOS MINISTERIOS (en el informe)
            ("MIN_FEMENIL", "Ministerio Femenil", "ingresos_ministerios", 10),
            ("MIN_HOMBRES", "Hombres de Honor", "ingresos_ministerios", 20),
            ("MIN_EMBAJADORES", "Embajadores de Cristo", "ingresos_ministerios", 30),
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

            # ENVÍOS A MINISTERIOS NACIONALES
            ("ENV_MIN_FEMENIL", "Ministerio Femenil", "envios_ministerios", 10),
            ("ENV_MIN_HOMBRES", "Hombres de Honor", "envios_ministerios", 20),
            ("ENV_MIN_EMBAJADORES", "Embajadores de Cristo", "envios_ministerios", 30),
            ("ENV_MIN_ESC_BIBLICA", "Escuela Bíblica", "envios_ministerios", 40),
            ("ENV_MIN_MISIONERITAS", "Misioneritas", "envios_ministerios", 50),
            ("ENV_MIN_MISIONEROS", "Misioneros", "envios_ministerios", 60),
            ("ENV_MIN_EXPLORADORES", "Exploradores", "envios_ministerios", 70),
            ("ENV_MIN_MDA", "MDA", "envios_ministerios", 80),
            ("ENV_MIN_MISIONES", "Misiones", "envios_ministerios", 90),
            ("ENV_MIN_OTROS", "Otros Ministerios", "envios_ministerios", 100),

            # APORTES ESPECIALES (abreviado como pediste: A_)
            ("A_EVANGELISMO", "Ministerio de Evangelismo", "aportes_especiales", 10),
            ("A_DESEAD", "DESEAD", "aportes_especiales", 20),
            ("A_PLANTACION", "Plantación de Iglesias", "aportes_especiales", 30),
            ("A_MISIONEROS", "Misioneros", "aportes_especiales", 40),
            ("A_HUERFANOS", "Huérfanos", "aportes_especiales", 50),
            ("A_ENVEJECIENTES", "Envejecientes", "aportes_especiales", 60),
            ("A_VULNERABLES", "Grupos Vulnerables", "aportes_especiales", 70),
            ("A_SORDOS", "Ministerio a los Sordos", "aportes_especiales", 80),
            ("A_DESARROLLO", "Desarrollo del Concilio", "aportes_especiales", 90),
        ]

        casilla_by_codigo = {}
        for codigo, nombre, seccion, orden in casillas:
            obj, _ = CasillaF001.objects.update_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "seccion": seccion,
                    "orden": orden,
                    "activo": True,
                },
            )
            casilla_by_codigo[codigo] = obj

        self.stdout.write(self.style.SUCCESS(f"✔ Casillas F.001 listas: {len(casilla_by_codigo)}"))

        # ------------------------------------------------------------
        # 2) CATEGORÍAS (lo que el usuario selecciona)
        #    Regla: ministerios en ingreso => 'Ofrenda ...'
        #           envíos egreso => 'Envío a ... Nacional'
        #           aportes => 'Aporte a ...'
        # ------------------------------------------------------------
        # Detectamos si existen campos nuevos (codigo, casilla_f001)
        categoria_fields = {f.name for f in CategoriaMovimiento._meta.get_fields()}
        has_codigo = "codigo" in categoria_fields
        has_casilla = "casilla_f001" in categoria_fields

        categorias = [
            # Ingresos iglesia
            ("ingreso", "Diezmos", "CAT_ING_DIEZMOS", "ING_DIEZMOS"),
            ("ingreso", "Ofrendas Voluntarias", "CAT_ING_OFRENDA_VOL", "ING_OFRENDA_VOL"),
            ("ingreso", "Ofrendas Especiales", "CAT_ING_OFRENDA_ESP", "ING_OFRENDA_ESP"),
            ("ingreso", "Otras Ofrendas", "CAT_ING_OTRAS_OFR", "ING_OTRAS_OFR"),
            ("ingreso", "Otros Ingresos", "CAT_ING_OTROS", "ING_OTROS"),
            ("ingreso", "Ayudas del Concilio", "CAT_ING_AYUDA_CONCILIO", "ING_AYUDA_CONCILIO"),
            ("ingreso", "Ofrendas del Exterior", "CAT_ING_EXTERIOR", "ING_EXTERIOR"),

            # Ingresos ministerios (como pediste)
            ("ingreso", "Ofrenda Ministerio Femenil", "CAT_MIN_FEMENIL", "MIN_FEMENIL"),
            ("ingreso", "Ofrenda Hombres de Honor", "CAT_MIN_HOMBRES", "MIN_HOMBRES"),
            ("ingreso", "Ofrenda Embajadores de Cristo", "CAT_MIN_EMBAJADORES", "MIN_EMBAJADORES"),
            ("ingreso", "Ofrenda Escuela Bíblica", "CAT_MIN_ESC_BIBLICA", "MIN_ESC_BIBLICA"),
            ("ingreso", "Ofrenda Misioneritas", "CAT_MIN_MISIONERITAS", "MIN_MISIONERITAS"),
            ("ingreso", "Ofrenda Exploradores", "CAT_MIN_EXPLORADORES", "MIN_EXPLORADORES"),
            ("ingreso", "Ofrenda MDA", "CAT_MIN_MDA", "MIN_MDA"),
            ("ingreso", "Ofrenda Misiones", "CAT_MIN_MISIONES", "MIN_MISIONES"),
            ("ingreso", "Ofrenda Otros Ministerios", "CAT_MIN_OTROS", "MIN_OTROS"),

            # Egresos base
            ("egreso", "Asignación Pastoral", "CAT_EGR_ASIG_PASTORAL", "EGR_ASIG_PASTORAL"),
            ("egreso", "Alquileres Casa/Templo", "CAT_EGR_ALQUILER", "EGR_ALQUILER"),
            ("egreso", "Evangelismo y Misiones", "CAT_EGR_EVANGELISMO", "EGR_EVANGELISMO"),
            ("egreso", "Agua, Luz, Teléfono", "CAT_EGR_SERVICIOS", "EGR_SERVICIOS"),
            ("egreso", "Ayuda a Capillas", "CAT_EGR_CAPILLAS", "EGR_CAPILLAS"),
            ("egreso", "Ayuda a Necesitados", "CAT_EGR_NECESITADOS", "EGR_NECESITADOS"),
            ("egreso", "Mantenimientos Varios", "CAT_EGR_MANTENIMIENTO", "EGR_MANTENIMIENTO"),
            ("egreso", "Apoyo a Minist. Locales", "CAT_EGR_APOYO_MIN", "EGR_APOYO_MIN"),
            ("egreso", "Otras Salidas", "CAT_EGR_OTRAS", "EGR_OTRAS"),

            # Envíos nacionales (contexto distinto)
            ("egreso", "Envío a Ministerio Femenil Nacional", "CAT_ENV_FEMENIL", "ENV_MIN_FEMENIL"),
            ("egreso", "Envío a Hombres de Honor Nacional", "CAT_ENV_HOMBRES", "ENV_MIN_HOMBRES"),
            ("egreso", "Envío a Embajadores Nacional", "CAT_ENV_EMBAJADORES", "ENV_MIN_EMBAJADORES"),
            ("egreso", "Envío a Escuela Bíblica Nacional", "CAT_ENV_ESC_BIBLICA", "ENV_MIN_ESC_BIBLICA"),
            ("egreso", "Envío a Misioneritas Nacional", "CAT_ENV_MISIONERITAS", "ENV_MIN_MISIONERITAS"),
            ("egreso", "Envío a Misioneros Nacional", "CAT_ENV_MISIONEROS", "ENV_MIN_MISIONEROS"),
            ("egreso", "Envío a Exploradores Nacional", "CAT_ENV_EXPLORADORES", "ENV_MIN_EXPLORADORES"),
            ("egreso", "Envío a MDA Nacional", "CAT_ENV_MDA", "ENV_MIN_MDA"),
            ("egreso", "Envío a Misiones Nacional", "CAT_ENV_MISIONES", "ENV_MIN_MISIONES"),
            ("egreso", "Envío a Otros Ministerios Nacional", "CAT_ENV_OTROS", "ENV_MIN_OTROS"),

            # Aportes especiales (A_)
            ("egreso", "Aporte a Ministerio de Evangelismo", "CAT_A_EVANGELISMO", "A_EVANGELISMO"),
            ("egreso", "Aporte a DESEAD", "CAT_A_DESEAD", "A_DESEAD"),
            ("egreso", "Aporte a Plantación de Iglesias", "CAT_A_PLANTACION", "A_PLANTACION"),
            ("egreso", "Aporte a Misioneros", "CAT_A_MISIONEROS", "A_MISIONEROS"),
            ("egreso", "Aporte a Huérfanos", "CAT_A_HUERFANOS", "A_HUERFANOS"),
            ("egreso", "Aporte a Envejecientes", "CAT_A_ENVEJECIENTES", "A_ENVEJECIENTES"),
            ("egreso", "Aporte a Grupos Vulnerables", "CAT_A_VULNERABLES", "A_VULNERABLES"),
            ("egreso", "Aporte a Sordos", "CAT_A_SORDOS", "A_SORDOS"),
            ("egreso", "Aporte a Desarrollo del Concilio", "CAT_A_DESARROLLO", "A_DESARROLLO"),
        ]

        creadas = 0
        for tipo, nombre, codigo_cat, casilla_codigo in categorias:
            defaults = {
                "activo": True,
                "es_editable": False,  # oficiales
            }
            if has_codigo:
                defaults["codigo"] = codigo_cat
            if has_casilla:
                defaults["casilla_f001"] = casilla_by_codigo[casilla_codigo]

            # Único por (nombre,tipo) según tu constraint
            obj, created = CategoriaMovimiento.objects.update_or_create(
                nombre=nombre,
                tipo=tipo,
                defaults=defaults,
            )
            if created:
                creadas += 1

        self.stdout.write(self.style.SUCCESS(f"✔ Categorías oficiales listas ({len(categorias)}). Nuevas: {creadas}"))

        # ------------------------------------------------------------
        # 3) CUENTAS BASE
        # ------------------------------------------------------------
        cuentas = [
            ("Caja General", "caja", moneda, "Cuenta base del sistema (efectivo)."),
            ("Banco Principal", "banco", moneda, "Cuenta base del sistema (banco)."),
        ]

        for nombre, tipo, moneda_cuenta, descripcion in cuentas:
            CuentaFinanciera.objects.update_or_create(
                nombre=nombre,
                defaults={
                    "tipo": tipo,
                    "moneda": moneda_cuenta,
                    "descripcion": descripcion,
                    "saldo_inicial": Decimal("0.00"),
                    "esta_activa": True,
                },
            )

        self.stdout.write(self.style.SUCCESS("✔ Cuentas base listas."))
        self.stdout.write(self.style.SUCCESS("✅ SEED FINANZAS COMPLETADO."))
