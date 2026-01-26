# ══════════════════════════════════════════════════════════════════════════════
# ARCHIVO 4: management/commands/generar_thumbnails.py
# ══════════════════════════════════════════════════════════════════════════════
#
# UBICACIÓN: miembros_app/management/commands/generar_thumbnails.py
#
# IMPORTANTE: Crear la estructura de carpetas:
#   miembros_app/
#   └── management/
#       └── __init__.py  (vacío)
#       └── commands/
#           └── __init__.py  (vacío)
#           └── generar_thumbnails.py  (este archivo)
#
# USO: python manage.py generar_thumbnails
#
# ══════════════════════════════════════════════════════════════════════════════

from django.core.management.base import BaseCommand
import cloudinary.uploader


class Command(BaseCommand):
    help = 'Genera thumbnails para fotos de miembros existentes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se haría, sin ejecutar',
        )
    
    def handle(self, *args, **options):
        # Importar aquí para evitar problemas de import circular
        from miembros_app.models import Miembro
        
        dry_run = options['dry_run']
        
        # Obtener miembros con foto
        miembros = Miembro.objects.exclude(foto__isnull=True).exclude(foto='')
        total = miembros.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('No hay miembros con foto.'))
            return
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Generando thumbnails para {total} miembros")
        self.stdout.write(f"{'='*60}\n")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se ejecutarán cambios\n'))
        
        exitosos = 0
        errores = 0
        
        for i, miembro in enumerate(miembros, 1):
            nombre = f"{miembro.nombres} {miembro.apellidos}"
            
            try:
                # Obtener public_id de Cloudinary
                if hasattr(miembro.foto, 'public_id'):
                    public_id = miembro.foto.public_id
                else:
                    # Si es string, extraer public_id de la URL
                    url = str(miembro.foto)
                    # Ejemplo: .../upload/v123/miembros/fotos/abc123.jpg
                    # public_id sería: miembros/fotos/abc123
                    import re
                    match = re.search(r'/upload/(?:v\d+/)?(.+?)(?:\.[^.]+)?$', url)
                    if match:
                        public_id = match.group(1)
                    else:
                        raise ValueError(f"No se pudo extraer public_id de: {url}")
                
                self.stdout.write(f"[{i}/{total}] {nombre}")
                self.stdout.write(f"         public_id: {public_id}")
                
                if not dry_run:
                    # Usar explicit() para generar eager transforms
                    result = cloudinary.uploader.explicit(
                        public_id,
                        type='upload',
                        eager=[
                            {
                                'width': 100, 
                                'height': 100, 
                                'crop': 'fill', 
                                'gravity': 'face',
                                'quality': 'auto',
                                'fetch_format': 'auto'
                            },
                            {
                                'width': 200, 
                                'height': 200, 
                                'crop': 'fill', 
                                'gravity': 'face',
                                'quality': 'auto',
                                'fetch_format': 'auto'
                            },
                        ],
                        eager_async=True,
                    )
                    self.stdout.write(self.style.SUCCESS(f"         ✓ Thumbnails generados"))
                else:
                    self.stdout.write(f"         → Se generarían thumbnails 100x100 y 200x200")
                
                exitosos += 1
                
            except Exception as e:
                errores += 1
                self.stdout.write(self.style.ERROR(f"         ✗ Error: {e}"))
        
        # Resumen
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"RESUMEN:")
        self.stdout.write(f"  Total procesados: {total}")
        self.stdout.write(self.style.SUCCESS(f"  Exitosos: {exitosos}"))
        if errores:
            self.stdout.write(self.style.ERROR(f"  Errores: {errores}"))
        self.stdout.write(f"{'='*60}\n")
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\nEjecuta sin --dry-run para aplicar los cambios:\n'
                '  python manage.py generar_thumbnails\n'
            ))