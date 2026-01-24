# core/services/welcome_messages.py
"""
🧠 SOID - Sistema de Mensajes de Bienvenida
Simple, humano, sin gamificación.
"""

import random
from django.utils import timezone


class WelcomeMessageService:
    """Genera mensajes de bienvenida contextuales."""
    
    # ═══════════════════════════════════════════════════════════════
    # 📚 BANCO DE MENSAJES
    # ═══════════════════════════════════════════════════════════════
    
    MENSAJES_PRIMERA_VEZ = [
        "🎉 ¡Bienvenido a la familia, {nombre}! Es tu primera vez aquí",
        "👋 ¡Hola {nombre}! Qué emoción tenerte por primera vez en SOID",
        "🌟 ¡{nombre}! Bienvenido a bordo. Esto es el comienzo de algo grande",
        "🚀 ¡Primera vez aquí, {nombre}! Estoy para ayudarte",
        "✨ ¡{nombre}! Como dice Isaías: 'He aquí, hago cosa nueva'. ¡Bienvenido!",
        "🙌 ¡{nombre}, bienvenido! 'El que comenzó la buena obra, la perfeccionará'",
    ]
    
    MENSAJES_AUSENCIA_LARGA = [
        "¡{nombre}! Pensé que no volverías... 🙈 ¡Qué bueno verte!",
        "¡Mira quién decidió aparecer! Bienvenido de vuelta, {nombre} 😄",
        "¿{nombre}? ¿Eres tú? ¡Hacía {dias} días que no te veía!",
        "¡El hijo pródigo ha vuelto! Bienvenido, {nombre} 🎉",
        "¡{nombre}! Ya preparaba los carteles de 'Se busca' 😅",
        "Como dice el Salmo: 'Grandes cosas ha hecho el Señor... ¡{nombre} volvió!' 😊",
    ]
    
    MENSAJES_AUSENCIA_MEDIA = [
        "¡{nombre}! Ya te estábamos extrañando",
        "¡Bienvenido de vuelta, {nombre}! Han pasado unos días...",
        "¡{nombre}! El sistema se sentía solo sin ti 😊",
    ]
    
    MENSAJES_HORA = {
        'madrugada': [
            "¿{nombre} a estas horas? ¡El que madruga, Dios le ayuda! ☕",
            "¡{nombre}! ¿Tampoco puedes dormir? 🌙",
            "¡Wow! {nombre} trabajando de madrugada. ¡Qué dedicación! 💪",
        ],
        'manana': [
            "¡Buenos días, {nombre}! ☀️",
            "¡{nombre}! Comenzando el día con energía 💪",
            "¡Buen día, {nombre}! 'Este es el día que hizo el Señor' 🙏",
        ],
        'tarde': [
            "¡Buenas tardes, {nombre}!",
            "¡{nombre}! Espero que hayas almorzado bien 🍽️",
            "¡Hola {nombre}! Tarde perfecta para avanzar",
        ],
        'noche': [
            "¡Buenas noches, {nombre}! 🌙",
            "¡{nombre}! Cerrando el día con broche de oro 🌟",
        ],
    }
    
    MENSAJES_LIDER = [
        "¡Bienvenido, líder {nombre}! Tu equipo te necesita 💪",
        "¡{nombre}! El capitán ha llegado 🚀",
        "¡Hola Pastor {nombre}! 'Apacienta mis ovejas' 🐑",
        "¡{nombre}! Como Nehemías, tú edificas vidas 🏗️",
        "¡Bienvenido {nombre}! El buen pastor conoce sus ovejas 😉",
        "¡Qué susto! {nombre}! Pensé que era el Pastor 😉",
        "😏 Atención… ha llegado {nombre}. Ahora sí se puede trabajar.",
        "👑 Señoras y señores… {nombre} ha entrado. Mantengan la calma.",
        "🫡 Saludos, líder {nombre}. El sistema estaba esperando órdenes.",
        "🔥 {nombre} ha llegado. Nivel de liderazgo: activado.",
        "🐑 Pastor {nombre}, el rebaño está presente… y el sistema también.",
        "🏗️ Como Nehemías… {nombre} ha vuelto a la obra.",
        "😄 {nombre}, pensé que hoy nos dejabas solos… pero no.",
        "🛡️ Líder {nombre} detectado. Permisos concedidos.",
        "📜 {nombre}, el consejo se reúne… aunque sea en el sistema.",
        "¡{nombre}! El arquitecto del sistema ha llegado 🏛️",
        "¡Bienvenido Admin {nombre}! Todo bajo control... creo 😅",
        "¡{nombre}! Con gran poder viene gran responsabilidad 🦸",
        "¡{nombre}! Como José en Egipto, todo está bajo tu mano 📊",
    ]

    MENSAJES_ADMIN = [
        "🏛️ Bienvenido, {nombre}. El sistema está bajo tu gobierno.",
        "👑 {nombre}, el arquitecto del sistema ha llegado.",
        "📊 {nombre}, todo está listo para tu supervisión.",
        "⚖️ Administrador {nombre}, el orden ha sido restablecido.",
        "😏 Ah… llegó {nombre}. Ahora sí hay auditoría.",
        "😂 {nombre} ha entrado. Los bugs están nerviosos.",
        "🛡️ Atención… {nombre} está en línea. Compórtense.",
        "🤭 {nombre}, el sistema funcionaba… hasta que llegaste 😅",
        "💻 {nombre}, como Moisés… separaste el caos del orden.",
        "📖 {nombre}, hoy no abriste el mar… pero sí la base de datos.",
        "🧠 {nombre}, el primer admin bíblico fue José en Egipto.",
        "🐛 {nombre}, los errores se esconden… pero tú los encuentras.",
        "🏰 Las puertas del sistema se abren para {nombre}.",
        "⚔️ {nombre} ha cruzado el umbral del servidor.",
        "🔥 {nombre}, el núcleo del sistema reconoce tu autoridad.",
        "🚀 {nombre} ha iniciado sesión. Modo administrador activado.",
    ]
    
    MENSAJES_SECRETARIA = [
        "¡{nombre}! La persona más organizada ha llegado 📋",
        "¡Bienvenida {nombre}! Sin ti, esto sería un caos 💫",
        "¡Hola {nombre}! Como Débora, eres pilar aquí 🌟",
    ]
    
    MENSAJES_NORMALES = [
        "¡Hola {nombre}! Bienvenido 👋",
        "¡{nombre}! Qué bueno verte",
        "¡Bienvenido {nombre}!",
    ]
    
    CHISTES_BIBLICOS = [
        "💡 ¿Sabías que el primer distanciamiento social está en Números 2?",
        "😄 ¿Por qué los apóstoles eran malos en matemáticas? Solo sabían multiplicar panes",
        "📖 El primer 'tweet' fue la paloma de Noé anunciando tierra firme",
        "🤔 Moisés fue el primer líder en usar la nube para guiar a su equipo",
        "😅 El WiFi más antiguo: Babel... ¡todos hablaban el mismo idioma!",
        "🎵 David era el primer cantautor con playlist de éxitos (los Salmos)",
        "📱 ¿El primer grupo de WhatsApp? Los 12 apóstoles",
        "🐋 Jonás tuvo el primer Uber submarino de la historia",
    ]
    
    MENSAJES_CUMPLEANOS = [
        "🎂 ¡¡¡FELIZ CUMPLEAÑOS {nombre}!!! 🎉🎈🎁",
        "🎂 ¡{nombre}! ¡Hoy es TU día! ¡Feliz cumpleaños! 🎉",
    ]

    # ═══════════════════════════════════════════════════════════════
    # 🧠 LÓGICA
    # ═══════════════════════════════════════════════════════════════
    
    @classmethod
    def get_welcome_message(cls, user, previous_login=None, soid_ctx=None):
        """Genera un mensaje de bienvenida."""
        now = timezone.now()
        nombre = cls._get_display_name(user)
        rol = soid_ctx.get('rol', 'usuario') if soid_ctx else 'usuario'
        
        mensaje = None
        tipo = 'normal'
        icono = 'fa-hand-wave'
        extra = None
        
        # 0️⃣ Primera vez
        if previous_login is None:
            mensaje = random.choice(cls.MENSAJES_PRIMERA_VEZ).format(nombre=nombre)
            tipo = 'primera_vez'
            icono = 'fa-rocket'
            extra = "💡 Tip: Explora el menú lateral para conocer todas las funciones"
            return {'mensaje': mensaje, 'tipo': tipo, 'icono': icono, 'extra': extra}
        
        # 1️⃣ Cumpleaños
        if cls._is_user_birthday(user):
            mensaje = random.choice(cls.MENSAJES_CUMPLEANOS).format(nombre=nombre)
            tipo = 'cumpleanos'
            icono = 'fa-birthday-cake'
            return {'mensaje': mensaje, 'tipo': tipo, 'icono': icono, 'extra': None}
        
        # 2️⃣ Ausencia
        if previous_login and previous_login.login_at:
            dias_ausente = (now - previous_login.login_at).days
            
            if dias_ausente >= 7:
                mensaje = random.choice(cls.MENSAJES_AUSENCIA_LARGA).format(
                    nombre=nombre, dias=dias_ausente
                )
                tipo = 'ausencia_larga'
                icono = 'fa-face-surprise'
            elif dias_ausente >= 3:
                mensaje = random.choice(cls.MENSAJES_AUSENCIA_MEDIA).format(nombre=nombre)
                tipo = 'ausencia_media'
                icono = 'fa-face-smile-wink'
        
        # 3️⃣ Por rol
        if not mensaje:
            if rol == 'admin':
                mensaje = random.choice(cls.MENSAJES_ADMIN).format(nombre=nombre)
                tipo = 'admin'
                icono = 'fa-crown'
            elif rol == 'lider':
                mensaje = random.choice(cls.MENSAJES_LIDER).format(nombre=nombre)
                tipo = 'lider'
                icono = 'fa-people-group'
            elif rol == 'secretaria':
                mensaje = random.choice(cls.MENSAJES_SECRETARIA).format(nombre=nombre)
                tipo = 'secretaria'
                icono = 'fa-clipboard-list'
            else:
                # Por hora del día
                hora = now.hour
                if 0 <= hora < 6:
                    periodo = 'madrugada'
                elif 6 <= hora < 12:
                    periodo = 'manana'
                elif 12 <= hora < 18:
                    periodo = 'tarde'
                else:
                    periodo = 'noche'
                
                mensaje = random.choice(cls.MENSAJES_HORA[periodo]).format(nombre=nombre)
                tipo = periodo
                icono = cls._get_time_icon(periodo)
        
        # 4️⃣ Chiste (20% probabilidad)
        if random.random() < 0.2:
            extra = random.choice(cls.CHISTES_BIBLICOS)
        
        return {
            'mensaje': mensaje or random.choice(cls.MENSAJES_NORMALES).format(nombre=nombre),
            'tipo': tipo,
            'icono': icono,
            'extra': extra,
        }
    
    @classmethod
    def _get_display_name(cls, user):
        """Obtiene el nombre más amigable."""
        if hasattr(user, 'miembro') and user.miembro:
            miembro = user.miembro
            if hasattr(miembro, 'nombres') and miembro.nombres:
                return miembro.nombres.split()[0]
            if hasattr(miembro, 'nombre') and miembro.nombre:
                return miembro.nombre.split()[0]
        
        if user.first_name:
            return user.first_name
        
        return user.username.capitalize()
    
    @classmethod
    def _is_user_birthday(cls, user):
        """Verifica si hoy es cumpleaños."""
        today = timezone.now().date()
        
        if hasattr(user, 'miembro') and user.miembro:
            miembro = user.miembro
            for field in ['fecha_nacimiento', 'nacimiento', 'birthday', 'fecha_nac']:
                if hasattr(miembro, field):
                    birthday = getattr(miembro, field, None)
                    if birthday and hasattr(birthday, 'month'):
                        if birthday.month == today.month and birthday.day == today.day:
                            return True
        return False
    
    @classmethod
    def _get_time_icon(cls, periodo):
        """Retorna icono según hora."""
        icons = {
            'madrugada': 'fa-moon',
            'manana': 'fa-sun',
            'tarde': 'fa-cloud-sun',
            'noche': 'fa-star',
        }
        return icons.get(periodo, 'fa-hand-wave')