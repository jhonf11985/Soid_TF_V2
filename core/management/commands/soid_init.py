from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from core.models import Module, ConfiguracionSistema


class Command(BaseCommand):
    help = "Inicializa SOID: Configuración base, módulos oficiales y usuario admin."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("🚀 Ejecutando soid_init..."))

        # 1) Asegurar Configuración del sistema (singleton pk=1)
        config = ConfiguracionSistema.load()
        self.stdout.write(self.style.SUCCESS("✅ ConfiguracionSistema listo (pk=1)."))

        # 2) Módulos oficiales (sin cambiar codes para no romper nada)
        modulos_oficiales = [
            {
                "name": "Miembros",
                "code": "miembros_app",
                "description": "Gestión de los miembros de la iglesia",
                "icon": "groups",
                "color": "#4FC3F7",
                "url_name": "miembros_app:dashboard",
                "is_enabled": True,
                "order": 0,
            },
            {
                "name": "Configuracion",
                "code": "Configuracion",
                "description": "",
                "icon": "settings",
                "color": "#F06292",
                "url_name": "core:configuracion",
                "is_enabled": True,
                "order": 11,
            },
            {
                "name": "Asambleas y Votación",
                "code": "Votacion",
                "description": "",
                "icon": "how_to_vote",
                "color": "#7B8CDE",
                "url_name": "votacion:lista_votaciones",
                "is_enabled": True,
                "order": 8,
            },
            {
                "name": "Finanzas",
                "code": "Finanzas",
                "description": "",
                "icon": "account_balance_wallet",
                "color": "#FFD54F",
                "url_name": "finanzas_app:dashboard",
                "is_enabled": True,
                "order": 2,
            },
            {
                "name": "Estructura & Liderazgo",
                "code": "Estructura",
                "description": "",
                "icon": "account_tree",
                "color": "#FF8A80",
                "url_name": "estructura_app:dashboard",
                "is_enabled": True,
                "order": 3,
            },
            {
                "name": "Nuevo Creyente",
                "code": "nuevo_creyente",
                "description": "",
                "icon": "volunteer_activism",
                "color": "#4DB6AC",
                "url_name": "nuevo_creyente_app:nuevo_creyente",
                "is_enabled": True,
                "order": 1,
            },
            {
                "name": "Actualización de datos",
                "code": "ACTUALIZACION_DATOS_MIEMBROS",
                "description": "Para hacer actualizacion de miembros atraves de un link",
                "icon": "published_with_changes",
                "color": "#0EA5E9",
                "url_name": "actualizacion_datos_miembros:solicitudes_lista",
                "is_enabled": True,
                "order": 9,
            },
            {
                "name": "Recursos",
                "code": "inventario",
                "description": "",
                "icon": "inventory_2",
                "color": "#0097A7",
                "url_name": "inventario:inicio",
                "is_enabled": True,
                "order": 7,
            },
            {
                "name": "Agenda",
                "code": "agenda",
                "description": "",
                "icon": "event",
                "color": "#0097A7",
                "url_name": "agenda_app:home",
                "is_enabled": True,
                "order": 6,
            },
            {
                "name": "Evaluaciones",
                "code": "evaluaciones",
                "description": "",
                "icon": "leaderboard",
                "color": "#6f42c1",
                "url_name": "evaluaciones:dashboard",
                "is_enabled": True,
                "order": 5,
            },
            {
                "name": "Codigo QR",
                "code": "codigoqr",
                "description": "",
                "icon": "qr_code",
                "color": "#0097A7",
                "url_name": "codigo_qr:scan",
                "is_enabled": True,
                "order": 10,
            },
            {
                "name": "Formacion & Desarrollo",
                "code": "formacion",
                "description": "",
                "icon": "menu_book",
                "color": "#0097A7",
                "url_name": "formacion:inicio",
                "is_enabled": True,
                "order": 4,
            },
            {
                "name": "Portal de Miembro",
                "code": "perfil",
                "description": "",
                "icon": "groups",
                "color": "#0097A7",
                "url_name": "portal_miembros:perfil",
                "is_enabled": True,
                "order": 0,
            },
        ]

        creados = 0
        actualizados = 0

        for data in modulos_oficiales:
            code = data["code"]
            defaults = data.copy()
            defaults.pop("code", None)

            obj, created = Module.objects.update_or_create(code=code, defaults=defaults)
            if created:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Módulos listos: {creados} creados, {actualizados} actualizados."))

        # 3) Usuario admin fijo
        User = get_user_model()
        admin_username = "admin"
        admin_password = "admin123"

        admin_user, created = User.objects.get_or_create(username=admin_username, defaults={
            "is_active": True,
            "is_staff": True,
            "is_superuser": True,
        })

        # Si ya existía, asegurar flags (y que sea superuser)
        changed = False
        if not admin_user.is_active:
            admin_user.is_active = True
            changed = True
        if not admin_user.is_staff:
            admin_user.is_staff = True
            changed = True
        if not admin_user.is_superuser:
            admin_user.is_superuser = True
            changed = True

        # Siempre forzamos password fija (tú lo pediste)
        admin_user.set_password(admin_password)
        changed = True

        if changed:
            admin_user.save()

        if created:
            self.stdout.write(self.style.SUCCESS("✅ Usuario 'admin' creado como superusuario."))
        else:
            self.stdout.write(self.style.SUCCESS("✅ Usuario 'admin' verificado/actualizado como superusuario."))

        self.stdout.write(self.style.SUCCESS("🎉 soid_init terminado correctamente."))