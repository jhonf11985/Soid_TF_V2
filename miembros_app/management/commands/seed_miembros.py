import random
from datetime import date, timedelta
from io import BytesIO

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile

from miembros_app.models import Miembro

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_OK = True
except Exception:
    PIL_OK = False


NOMBRES_M = [
    "Juan", "Pedro", "Luis", "Carlos", "José", "Miguel", "Rafael", "Andrés", "Daniel", "Manuel",
    "Kelvin", "Jairo", "Alex", "Jahir", "Jonah", "Samuel", "Emanuel", "Wilmer", "Ricardo", "Francisco"
]
NOMBRES_F = [
    "María", "Ana", "Carmen", "Luisa", "Patricia", "Rosa", "Yolanda", "Claudia", "Laura", "Andrea",
    "Dariany", "Dariane", "Julieth", "Jaressi", "Yede", "Yeliany", "Paola", "Karina", "Maribel", "Yesenia"
]
APELLIDOS = [
    "Pérez", "García", "Rodríguez", "Martínez", "Hernández", "Gómez", "Díaz", "Ramírez", "Sánchez", "Castillo",
    "Melo", "Guerrero", "Del Rosario", "De la Cruz", "Santana", "Reyes", "Torres", "López"
]

SECTORES = [
    "Centro", "La Altagracia", "Villa Progreso", "Los Rosales", "El Millón", "San José",
    "La Otra Banda", "Yuma", "Savica", "San Martín", "Villa Cerro", "Villa Palmera"
]
CIUDADES = ["Higüey", "Punta Cana", "La Romana", "San Pedro", "Santo Domingo"]
PROVINCIAS = ["La Altagracia", "Santo Domingo", "San Cristóbal", "La Romana", "San Pedro de Macorís"]

ESTADOS = ["activo", "pasivo", "observacion"]


def _random_tel_rd() -> str:
    return random.choice(["809", "829", "849"]) + str(random.randint(1000000, 9999999))


def _safe_initials(nombre: str, apellido: str) -> str:
    a = (nombre[:1] or "X").upper()
    b = (apellido[:1] or "X").upper()
    return f"{a}{b}"


def _make_realistic_image_fast(width: int, height: int, initials: str) -> "Image.Image":
    """
    Imagen sintética tipo 'foto' rápida:
    - base color
    - textura con noise + blur (rápido, ejecuta en C)
    - unsharp mask
    - iniciales centradas
    """
    base = Image.new("RGB", (width, height), (
        random.randint(40, 180),
        random.randint(40, 180),
        random.randint(40, 180),
    ))

    # Textura rápida
    noise_strength = random.uniform(20, 60)
    noise = Image.effect_noise((width, height), noise_strength).convert("L")
    noise = noise.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.8, 1.8)))
    noise_rgb = Image.merge("RGB", (noise, noise, noise))

    img = Image.blend(base, noise_rgb, alpha=0.22)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))

    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", int(min(width, height) * 0.22))
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), initials, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (width - tw) / 2
    ty = (height - th) / 2

    draw.text((tx + 6, ty + 6), initials, fill=(0, 0, 0), font=font)
    draw.text((tx, ty), initials, fill=(255, 255, 255), font=font)

    return img


def _jpeg_bytes_target(img: "Image.Image", target_kb_min: int, target_kb_max: int) -> bytes:
    """
    Intenta acercarse al rango de KB variando 'quality'.
    (Sin bucles pesados ni reescalado agresivo).
    """
    last = b""

    for q in [95, 92, 90, 88, 85, 82, 80, 78, 75, 72, 70, 68, 65, 60, 55]:
        bio = BytesIO()
        img.save(bio, format="JPEG", quality=q, optimize=False, progressive=False)
        b = bio.getvalue()
        last = b
        kb = len(b) // 1024
        if target_kb_min <= kb <= target_kb_max:
            return b

    return last


class Command(BaseCommand):
    help = "Crea miembros de prueba aleatorios (con mezcla realista de imágenes)."

    def add_arguments(self, parser):
        parser.add_argument("--total", type=int, default=300, help="Cantidad de miembros a crear")
        parser.add_argument(
            "--imagenes-realistas",
            action="store_true",
            help="70%% fotos medianas, 20%% pesadas, 10%% sin foto",
        )

    def handle(self, *args, **options):
        total = options["total"]
        realistas = options["imagenes_realistas"]

        if realistas and not PIL_OK:
            self.stdout.write(self.style.ERROR("❌ Falta Pillow. Instala con: pip install Pillow"))
            return

        creados = 0
        con_foto = 0
        sin_foto = 0

        for _ in range(total):
            genero = random.choice(["masculino", "femenino"])
            nombre = random.choice(NOMBRES_M if genero == "masculino" else NOMBRES_F)
            apellido = random.choice(APELLIDOS)

            # Edad y fecha de nacimiento
            edad = random.randint(5, 75)
            fecha_nacimiento = date.today() - timedelta(days=edad * 365)

            telefono = _random_tel_rd()

            miembro = Miembro(
                nombres=nombre,
                apellidos=apellido,
                genero=genero,
                fecha_nacimiento=fecha_nacimiento,
                telefono=telefono,
                whatsapp=telefono,
                email=f"{nombre.lower()}.{apellido.lower()}{random.randint(1,999)}@correo.com",
                sector=random.choice(SECTORES),
                ciudad=random.choice(CIUDADES),
                provincia=random.choice(PROVINCIAS),
                estado_miembro=random.choice(ESTADOS),
                activo=True,
                nuevo_creyente=(random.random() < 0.15),      # 15% nuevos creyentes (NC-XXXX)
                bautizado_confirmado=(random.random() < 0.7),
            )

            # Importante: tu save() genera TF-XXXX / NC-XXXX y categoría edad
            miembro.save()

            if realistas:
                r = random.random()

                # 10% sin foto
                if r < 0.10:
                    sin_foto += 1
                else:
                    initials = _safe_initials(nombre, apellido)

                    # 70% medianas (150–300 KB) => 900x900
                    # 20% pesadas (600–1000 KB) => 1400x1400 (más realista que 1600, y más rápido)
                    if r < 0.90:
                        target_min, target_max = 150, 300
                        w, h = 900, 900
                    else:
                        target_min, target_max = 600, 1000
                        w, h = 1400, 1400

                    img = _make_realistic_image_fast(w, h, initials)
                    jpg = _jpeg_bytes_target(img, target_min, target_max)

                    filename = f"foto_{miembro.id}_{initials}.jpg"
                    miembro.foto.save(filename, ContentFile(jpg), save=True)
                    con_foto += 1

            creados += 1

        self.stdout.write(self.style.SUCCESS(f"✅ {creados} miembros creados."))
        if realistas:
            self.stdout.write(self.style.SUCCESS(f"🖼️ Con foto: {con_foto} | Sin foto: {sin_foto}"))
            self.stdout.write(self.style.SUCCESS("📌 Mezcla aprox: 70%% medianas, 20%% pesadas, 10%% sin foto."))
