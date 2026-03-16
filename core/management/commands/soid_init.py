import os

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from core.models import Module, ConfiguracionSistema
from tenants.models import Tenant


class Command(BaseCommand):
    help = "Inicializa SOID: configuración base, módulos oficiales y usuario admin."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            type=str,
            help='Slug o ID del tenant a inicializar (si no se especifica, crea/usa "default")',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("🚀 Ejecutando soid_init..."))

        default_tenant_slug = os.getenv("SOID_DEFAULT_TENANT_SLUG", "default")
        default_tenant_nombre = os.getenv("SOID_DEFAULT_TENANT_NOMBRE", "Iglesia Principal")
        default_tenant_dominio = os.getenv("SOID_DEFAULT_TENANT_DOMAIN", "localhost")

        admin_username = os.getenv("SOID_ADMIN_USER", "admin")
        admin_password = os.getenv("SOID_ADMIN_PASSWORD", "admin123")

        tenant_arg = options.get("tenant")

        if tenant_arg:
            tenant = None

            try:
                tenant = Tenant.objects.get(slug=tenant_arg)
            except Tenant.DoesNotExist:
                try:
                    tenant = Tenant.objects.get(pk=tenant_arg)
                except (Tenant.DoesNotExist, ValueError):
                    self.stdout.write(
                        self.style.ERROR(f"❌ Tenant '{tenant_arg}' no encontrado.")
                    )
                    return

            self.stdout.write(self.style.SUCCESS(f"✅ Usando tenant existente: '{tenant}'"))

        else:
            tenant = Tenant.objects.first()

            if tenant:
                self.stdout.write(self.style.SUCCESS(f"✅ Usando tenant existente: '{tenant}'"))
            else:
                tenant = Tenant.objects.create(
                    slug=default_tenant_slug,
                    nombre=default_tenant_nombre,
                    dominio=default_tenant_dominio,
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Tenant '{default_tenant_slug}' creado con dominio '{default_tenant_dominio}'."
                    )
                )

        ConfiguracionSistema.load(tenant)
        self.stdout.write(
            self.style.SUCCESS(f"✅ ConfiguracionSistema listo (tenant: {tenant}).")
        )

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
                "name": "Portal de Miembro",
                "code": "perfil",
                "description": "",
                "icon": "groups",
                "color": "#0097A7",
                "url_name": "portal_miembros:perfil",
                "is_enabled": True,
                "order": 1,
            },
            {
                "name": "Visitas",
                "code": "visitas",
                "description": "",
                "icon": "",
                "color": "#0097A7",
                "url_name": "visitas_app:registro_list",
                "is_enabled": True,
                "order": 2,
            },
            {
                "name": "Nuevo Creyente",
                "code": "nuevo_creyente",
                "description": "",
                "icon": "volunteer_activism",
                "color": "#4DB6AC",
                "url_name": "nuevo_creyente_app:nuevo_creyente",
                "is_enabled": True,
                "order": 3,
            },
            {
                "name": "Finanzas",
                "code": "Finanzas",
                "description": "",
                "icon": "account_balance_wallet",
                "color": "#FFD54F",
                "url_name": "finanzas_app:dashboard",
                "is_enabled": True,
                "order": 4,
            },
            {
                "name": "Estructura & Liderazgo",
                "code": "Estructura",
                "description": "",
                "icon": "account_tree",
                "color": "#FF8A80",
                "url_name": "estructura_app:dashboard",
                "is_enabled": True,
                "order": 5,
            },
            {
                "name": "Formacion & Desarrollo",
                "code": "formacion",
                "description": "",
                "icon": "menu_book",
                "color": "#0097A7",
                "url_name": "formacion:inicio",
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
                "order": 8,
            },
            {
                "name": "Recursos",
                "code": "inventario",
                "description": "",
                "icon": "inventory_2",
                "color": "#0097A7",
                "url_name": "inventario:inicio",
                "is_enabled": True,
                "order": 9,
            },
            {
                "name": "Asambleas y Votación",
                "code": "Votacion",
                "description": "",
                "icon": "how_to_vote",
                "color": "#7B8CDE",
                "url_name": "votacion:lista_votaciones",
                "is_enabled": True,
                "order": 10,
            },
            {
                "name": "Actualización de datos",
                "code": "ACTUALIZACION_DATOS_MIEMBROS",
                "description": "Para hacer actualizacion de miembros atraves de un link",
                "icon": "published_with_changes",
                "color": "#0EA5E9",
                "url_name": "actualizacion_datos_miembros:solicitudes_lista",
                "is_enabled": True,
                "order": 11,
            },
            {
                "name": "Codigo QR",
                "code": "codigoqr",
                "description": "",
                "icon": "qr_code",
                "color": "#0097A7",
                "url_name": "codigo_qr:scan",
                "is_enabled": True,
                "order": 12,
            },
            {
                "name": "Configuracion",
                "code": "Configuracion",
                "description": "",
                "icon": "settings",
                "color": "#F06292",
                "url_name": "core:configuracion",
                "is_enabled": True,
                "order": 13,
            },
        ]

        creados = 0
        actualizados = 0

        for data in modulos_oficiales:
            code = data["code"]
            defaults = data.copy()
            defaults.pop("code", None)

            obj, created = Module.objects.update_or_create(
                code=code,
                defaults=defaults,
            )

            if created:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Módulos listos: {creados} creados, {actualizados} actualizados."
            )
        )

        User = get_user_model()

        admin_user, created = User.objects.get_or_create(
            username=admin_username,
            defaults={
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )

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

        admin_user.set_password(admin_password)
        changed = True

        if changed:
            admin_user.save()

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Usuario '{admin_username}' creado como superusuario."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Usuario '{admin_username}' verificado/actualizado como superusuario."
                )
            )

        self.stdout.write(self.style.SUCCESS("🎉 soid_init terminado correctamente."))