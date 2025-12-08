from datetime import date

from django import forms
from django.db.models import Max

from core.utils_config import get_edad_minima_miembro_oficial, get_config
from .models import Miembro, MiembroRelacion



   

class MiembroForm(forms.ModelForm):
    # ==========================
    # LISTAS DESPLEGABLES
    # ==========================

    # Género obligatorio
    GENERO_CHOICES = [
    ("", "Seleccione género"),
    ("masculino", "Masculino"),
    ("femenino", "Femenino"),
    ]


    ESTADO_CIVIL_CHOICES = [
        ("", "Seleccione estado civil"),
        ("Soltero/a", "Soltero/a"),
        ("Casado/a", "Casado/a"),
        ("Divorciado/a", "Divorciado/a"),
        ("Viudo/a", "Viudo/a"),
        ("Unión libre", "Unión libre"),
    ]

    NIVEL_EDUCATIVO_CHOICES = [
        ("", "Seleccione nivel"),
        ("Primaria", "Primaria"),
        ("Secundaria", "Secundaria"),
        ("Técnico", "Técnico"),
        ("Universitario", "Universitario"),
        ("Postgrado", "Postgrado"),
        ("Otro", "Otro"),
    ]

    # Estado del miembro
    ESTADO_MIEMBRO_CHOICES = [
        ("", "Seleccione estado"),
        ("activo", "Activo"),
        ("pasivo", "Pasivo"),
        ("observacion", "En observación"),
        ("disciplina", "En disciplina"),
        ("catecumeno", "Catecúmeno"),
    ]

    # Tipo de sangre
    TIPO_SANGRE_CHOICES = [
        ("", "Seleccione tipo de sangre"),
        ("O+", "O+"),
        ("O-", "O-"),
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
        ("No sabe", "No sabe"),
    ]
        # Solo lectura: código que se mostrará arriba del formulario
    codigo_miembro_display = forms.CharField(
        label="Código de miembro",
        required=False,
        disabled=True,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "readonly": "readonly",
                "tabindex": "-1",
            }
        ),
    )

    # Campo solo lectura para mostrar el código del miembro
    codigo_miembro_display = forms.CharField(
        required=False,
        label="Código de miembro",
        widget=forms.TextInput(
            attrs={
                "readonly": "readonly",
                "class": "form-input",
                "tabindex": "-1",  # para que no se enfoque al navegar con tab
            }
        ),
    )

    # ==========================
    # CAMPOS PERSONALIZADOS
    # ==========================

    genero = forms.ChoiceField(
        choices=GENERO_CHOICES,
        required=True,
        label="Género",
    )


    estado_civil = forms.ChoiceField(
        choices=ESTADO_CIVIL_CHOICES,
        required=False,
    )

    nivel_educativo = forms.ChoiceField(
        choices=NIVEL_EDUCATIVO_CHOICES,
        required=False,
    )

    estado_miembro = forms.ChoiceField(
        choices=ESTADO_MIEMBRO_CHOICES,
        required=True,
        label="Estado del miembro",
    )

    tipo_sangre = forms.ChoiceField(
        choices=TIPO_SANGRE_CHOICES,
        required=False,
    )

    # NOTA:
    # categoria_miembro se mantiene en el modelo pero no se muestra en el form
    
    class Meta:
        model = Miembro
        exclude = (
            "fecha_creacion",
            "fecha_actualizacion",
            "categoria_edad",
            "categoria_miembro", 
            "nuevo_creyente",
            "numero_miembro",
            "codigo_miembro",


        )

        labels = {
            "nombres": "Nombres",
            "apellidos": "Apellidos",
            "genero": "Género",
            "fecha_nacimiento": "Fecha de nacimiento",
            "lugar_nacimiento": "Lugar de nacimiento",
            "nacionalidad": "Nacionalidad",
            "estado_civil": "Estado civil",
            "nivel_educativo": "Nivel educativo",
            "profesion": "Profesión",
            "cedula": "Cédula",              # ✔ CORREGIDO
             "pasaporte": "Pasaporte", 
                    

            "telefono": "Teléfono",
            "telefono_secundario": "Teléfono secundario",
            "whatsapp": "WhatsApp",
            "email": "Correo electrónico",
            "direccion": "Dirección",
            "sector": "Sector / Barrio",
            "ciudad": "Ciudad",
            "provincia": "Provincia",
            "codigo_postal": "Código postal",

            "contacto_emergencia_nombre": "Nombre contacto de emergencia",
            "contacto_emergencia_telefono": "Teléfono de emergencia",
            "contacto_emergencia_relacion": "Relación con el contacto",

            "tipo_sangre": "Tipo de sangre",
            "alergias": "Alergias",
            "condiciones_medicas": "Condiciones médicas",
            "medicamentos": "Medicamentos",

            "empleador": "Lugar de trabajo",
            "puesto": "Puesto",
            "telefono_trabajo": "Teléfono del trabajo",
            "direccion_trabajo": "Dirección del trabajo",

            "estado_miembro": "Estado del miembro",
            "es_trasladado": "Viene de otra iglesia",
            "fecha_ingreso_iglesia": "Fecha de ingreso a la iglesia",
            "iglesia_anterior": "Iglesia anterior",
            "fecha_conversion": "Fecha de conversión",
            "fecha_bautismo": "Fecha de bautismo",
            "bautizado_confirmado": "Bautismo confirmado",

            "mentor": "Mentor",
            "lider_celula": "Líder de célula",

            "intereses": "Intereses",
            "habilidades": "Habilidades",
            "otros_intereses": "Otros intereses",
            "otras_habilidades": "Otras habilidades",

            "notas": "Notas pastorales",
            "foto": "Fotografía",

            # NUEVOS CAMPOS DE SALIDA
            "activo": "Miembro activo",
            "razon_salida": "Razón de salida",
            "fecha_salida": "Fecha de salida",
            "comentario_salida": "Comentario de salida",
        }

        widgets = {
            "nombres": forms.TextInput(attrs={"placeholder": "Introduce los nombres"}),
            "apellidos": forms.TextInput(attrs={"placeholder": "Introduce los apellidos"}),
            "fecha_nacimiento": forms.DateInput(
                attrs={
                    "type": "date",
                    "min": "1900-01-01",
                    "max": date.today().isoformat(),
                }
            ),
            "lugar_nacimiento": forms.TextInput(attrs={"placeholder": "Ciudad o lugar de nacimiento"}),
            "nacionalidad": forms.TextInput(attrs={"placeholder": "Ejemplo: Dominicana"}),
            "profesion": forms.TextInput(attrs={"placeholder": "Ej: Maestro, Ingeniero…"}),

            "telefono": forms.TextInput(attrs={"type": "tel", "placeholder": "Teléfono principal"}),
            "telefono_secundario": forms.TextInput(attrs={"type": "tel", "placeholder": "Teléfono secundario"}),
            "whatsapp": forms.TextInput(attrs={"type": "tel", "placeholder": "WhatsApp"}),
            "email": forms.EmailInput(attrs={"placeholder": "correo@ejemplo.com"}),

            "direccion": forms.Textarea(attrs={"rows": 2, "placeholder": "Calle, número, referencia…"}),
            "sector": forms.TextInput(attrs={"placeholder": "Sector o barrio"}),
            "ciudad": forms.TextInput(attrs={"placeholder": "Ciudad"}),
            "provincia": forms.TextInput(attrs={"placeholder": "Provincia"}),
            "codigo_postal": forms.TextInput(attrs={"placeholder": "Código postal"}),

            
            # 👇 AQUÍ EL WIDGET DE CÉDULA
            "cedula": forms.TextInput(
                attrs={
                    "placeholder": "000-0000000-0",
                    "maxlength": "13",          # 11 dígitos + 2 guiones
                    "inputmode": "numeric",     # en móvil abre teclado numérico
                    "autocomplete": "off",
                }
            ),
            "pasaporte": forms.TextInput(
                attrs={
                    "placeholder": "Número de pasaporte",
                }
            ),
            "contacto_emergencia_nombre": forms.TextInput(attrs={"placeholder": "Nombre completo"}),
            "contacto_emergencia_telefono": forms.TextInput(attrs={"type": "tel", "placeholder": "Teléfono de emergencia"}),
            "contacto_emergencia_relacion": forms.TextInput(attrs={"placeholder": "Ej: Madre, Padre…"}),

            "alergias": forms.Textarea(attrs={"rows": 2, "placeholder": "Alergias conocidas"}),
            "condiciones_medicas": forms.Textarea(attrs={"rows": 3, "placeholder": "Condiciones médicas"}),
            "medicamentos": forms.Textarea(attrs={"rows": 2, "placeholder": "Medicamentos actuales"}),

            "empleador": forms.TextInput(attrs={"placeholder": "Empresa o lugar de trabajo"}),
            "puesto": forms.TextInput(attrs={"placeholder": "Puesto"}),
            "telefono_trabajo": forms.TextInput(attrs={"type": "tel", "placeholder": "Teléfono del trabajo"}),
            "direccion_trabajo": forms.Textarea(attrs={"rows": 2, "placeholder": "Dirección del trabajo"}),

            "fecha_ingreso_iglesia": forms.DateInput(
                attrs={
                    "type": "date",
                    "min": "1900-01-01",
                    "max": date.today().isoformat(),
                }
            ),
            "fecha_conversion": forms.DateInput(
                attrs={
                    "type": "date",
                    "min": "1900-01-01",
                    "max": date.today().isoformat(),
                }
            ),
            "fecha_bautismo": forms.DateInput(
                attrs={
                    "type": "date",
                    "min": "1900-01-01",
                    "max": date.today().isoformat(),
                }
            ),

            # NUEVO: FECHA DE SALIDA CON FORMATO DATE
            "fecha_salida": forms.DateInput(
                attrs={
                    "type": "date",
                    "min": "1900-01-01",
                    "max": date.today().isoformat(),
                }
            ),

            "intereses": forms.Textarea(attrs={"rows": 2, "placeholder": "Áreas de interés"}),
            "otros_intereses": forms.Textarea(attrs={"rows": 2, "placeholder": "Otros intereses"}),
            "habilidades": forms.Textarea(attrs={"rows": 2, "placeholder": "Habilidades"}),
            "otras_habilidades": forms.Textarea(attrs={"rows": 2, "placeholder": "Otras habilidades"}),

            "notas": forms.Textarea(attrs={"rows": 3, "placeholder": "Notas pastorales"}),

            "foto": forms.ClearableFileInput(attrs={"accept": "image/*"}),

            # NUEVO: COMENTARIO DE SALIDA (opcional)
            "comentario_salida": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "Detalles breves sobre el motivo de salida (opcional)…",
                }
            ),
        }

    # ==========================
    # VALIDACIONES / LÓGICA DE NEGOCIO
    # ==========================
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Fecha de conversión por defecto (como ya lo tenías)
        if not self.instance.pk and not self.initial.get("fecha_conversion"):
            self.initial["fecha_conversion"] = date.today()

        # === CÓDIGO PREVIO DE MIEMBRO, USANDO CONFIGURACIÓN ===
        cfg = get_config()
        prefijo = getattr(cfg, "codigo_miembro_prefijo", "TF-") or "TF-"

        if self.instance and self.instance.pk:
            # Modo editar: mostramos el código real del miembro
            self.fields["codigo_miembro_display"].initial = self.instance.codigo_miembro
        else:
            # Modo crear: calculamos el siguiente número y lo mostramos con el prefijo
            ultimo = Miembro.objects.aggregate(Max("numero_miembro"))["numero_miembro__max"] or 0
            siguiente = ultimo + 1
            self.fields["codigo_miembro_display"].initial = f"{prefijo}{siguiente:04d}"

        # --- CAMPOS OBLIGATORIOS EXTRA ---
        # Estos dos deben venir siempre rellenados
        self.fields["fecha_nacimiento"].required = True
        self.fields["estado_miembro"].required = True

    def _calcular_edad_desde_fecha(self, fecha):
        """Devuelve la edad en años a partir de una fecha de nacimiento."""
        if not fecha:
            return None
        hoy = date.today()
        edad = hoy.year - fecha.year - (
            (hoy.month, hoy.day) < (fecha.month, fecha.day)
        )
        return edad


    def clean(self):
        cleaned_data = super().clean()

        fecha_nacimiento = cleaned_data.get("fecha_nacimiento")
        estado_miembro = cleaned_data.get("estado_miembro")
        fecha_bautismo = cleaned_data.get("fecha_bautismo")
        bautizado_confirmado = cleaned_data.get("bautizado_confirmado")
        iglesia_anterior = cleaned_data.get("iglesia_anterior")
        es_trasladado = cleaned_data.get("es_trasladado")

        edad = self._calcular_edad_desde_fecha(fecha_nacimiento)
        edad_minima = get_edad_minima_miembro_oficial()

        # ---------------------------------------
        # 1) LÓGICA DE TRASLADO / IGLESIA ANTERIOR
        # ---------------------------------------
        if not es_trasladado:
            # Si no viene trasladado, limpiamos la iglesia anterior
            cleaned_data["iglesia_anterior"] = ""
        else:
            # Si marcó que viene trasladado pero no indicó iglesia,
            # pedimos que lo complete (o desmarque la casilla).
            if not iglesia_anterior:
                self.add_error(
                    "iglesia_anterior",
                    "Indica la iglesia anterior del miembro o desmarca la opción de traslado.",
                )

        # ---------------------------------------
        # 2) LÓGICA DE BAUTISMO SEGÚN EDAD Y ESTADO
        # ---------------------------------------
        # Regla base:
        #   - Todos los estados pastorales (activo, pasivo, observación,
        #     disciplina, descarriado) representan miembros bautizados.
        #   - El estado 'catecumeno' nunca se marca como bautizado.
        #   - Los menores de edad mínima nunca se consideran 'bautizado_confirmado'.
        estados_bautizados = ["activo", "pasivo", "observacion", "disciplina", "descarriado"]

        if edad is not None and edad < edad_minima:
            # Menor de la edad mínima -> no bautizado confirmado
            cleaned_data["bautizado_confirmado"] = False
        else:
            if estado_miembro == "catecumeno":
                cleaned_data["bautizado_confirmado"] = False
            elif estado_miembro in estados_bautizados:
                cleaned_data["bautizado_confirmado"] = True
            else:
                # Otros estados futuros -> respetamos lo que ponga el usuario
                cleaned_data["bautizado_confirmado"] = bool(bautizado_confirmado)

        bautizado_final = cleaned_data.get("bautizado_confirmado")

        # No permitir registrar fecha de bautismo si no está marcado como bautizado
        if not bautizado_final and fecha_bautismo:
            self.add_error(
                "fecha_bautismo",
                "No puedes registrar una fecha de bautismo para un miembro no bautizado.",
            )

        # ---------------------------------------
        # 3) LÓGICA DE SALIDA (activo / inactivo)
        # ---------------------------------------
        activo = cleaned_data.get("activo")
        razon_salida = cleaned_data.get("razon_salida")
        fecha_salida = cleaned_data.get("fecha_salida")
        comentario_salida = cleaned_data.get("comentario_salida")
        fecha_ingreso = cleaned_data.get("fecha_ingreso_iglesia")
        hoy = date.today()

        if activo:
            # Si el miembro es activo, limpiamos cualquier dato de salida residual
            cleaned_data["razon_salida"] = None
            cleaned_data["fecha_salida"] = None
            cleaned_data["comentario_salida"] = ""
        else:
            # Miembro inactivo -> debe tener al menos una razón de salida
            if not razon_salida:
                self.add_error(
                    "razon_salida",
                    "Debes indicar la razón por la que el miembro deja de pertenecer a la iglesia.",
                )

            # Si no se indica fecha de salida, usamos la fecha actual
            if not fecha_salida:
                cleaned_data["fecha_salida"] = hoy
                fecha_salida = hoy

            # No permitir fechas futuras
            if fecha_salida and fecha_salida > hoy:
                self.add_error(
                    "fecha_salida",
                    "La fecha de salida no puede ser una fecha futura.",
                )

            # No permitir que la fecha de salida sea anterior a la fecha de ingreso
            if fecha_ingreso and fecha_salida and fecha_salida < fecha_ingreso:
                self.add_error(
                    "fecha_salida",
                    "La fecha de salida no puede ser anterior a la fecha de ingreso a la iglesia.",
                )

        # ---------------------------------------
        # 4) ESTADO OBLIGATORIO SI ES MAYOR O IGUAL A LA EDAD MÍNIMA
        # ---------------------------------------
        if edad is not None and edad >= edad_minima:
            # Si supera o iguala la edad mínima establecida, debe tener estado
            if not estado_miembro:  # "", None, etc.
                self.add_error(
                    "estado_miembro",
                    f"Debe seleccionar un estado porque este miembro tiene {edad} años y supera la edad mínima establecida ({edad_minima}).",
                )

        return cleaned_data

class NuevoCreyenteForm(forms.ModelForm):
    """
    Formulario sencillo para registrar nuevos creyentes.
    Usa el mismo modelo Miembro, pero con pocos campos esenciales,
    pensado para usarse rápido desde el móvil.
    """

    class Meta:
        model = Miembro
        fields = [
            "nombres",
            "apellidos",
            "genero",
            "fecha_nacimiento",
            "telefono",
            "whatsapp",
            "email",
            "direccion",
            "fecha_conversion",
            "notas",
        ]

        widgets = {
            "fecha_conversion": forms.DateInput(attrs={"type": "date"}),
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}),

            "telefono": forms.TextInput(
                attrs={
                    "type": "tel",
                    "placeholder": "Teléfono principal",
                    "autocomplete": "off",
                }
            ),
            "notas": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "Notas breves (opcional)",
                }
            ),

            "whatsapp": forms.TextInput(
                attrs={
                    "type": "tel",
                    "placeholder": "WhatsApp (opcional)",
                    "autocomplete": "off",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "correo@ejemplo.com (opcional)",
                    "autocomplete": "off",
                }
            ),
            "direccion": forms.TextInput(
                attrs={
                    "placeholder": "Dirección / Sector",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si es un registro nuevo, proponemos la fecha de hoy en el formulario
        if not self.instance.pk and not self.initial.get("fecha_conversion"):
            self.initial["fecha_conversion"] = date.today()

    def save(self, commit=True):
        miembro = super().save(commit=False)

        # Asegurar que lo vacío venga como None
        fecha_conv = self.cleaned_data.get("fecha_conversion")

        # Si el usuario la dejó vacía → poner la fecha de hoy
        if not fecha_conv:
            miembro.fecha_conversion = date.today()
        else:
            miembro.fecha_conversion = fecha_conv

        # Marcar como nuevo creyente
        miembro.nuevo_creyente = True

        # Nunca debe ser tratado como miembro oficial todavía
        miembro.estado_miembro = ""
        miembro.bautizado_confirmado = False
        miembro.fecha_bautismo = None

        # Asegurar que quede activo en el sistema
        if miembro.activo is None:
            miembro.activo = True

        if commit:
            miembro.save()

        return miembro

class MiembroRelacionForm(forms.ModelForm):
    """
    Formulario para gestionar los familiares (relaciones entre miembros).
    Lo usaremos solo en la pestaña 'Familiares'.
    """
    class Meta:
        model = MiembroRelacion
        fields = ["familiar", "tipo_relacion", "vive_junto", "es_responsable", "notas"]
        labels = {
            "familiar": "Miembro familiar",
            "tipo_relacion": "Relación",
            "vive_junto": "Vive en la misma casa",
            "es_responsable": "Responsable principal",
            "notas": "Notas (opcional)",
        }
        widgets = {
            "familiar": forms.Select(attrs={"class": "input", "style": "width:100%;"}),
            "tipo_relacion": forms.Select(attrs={"class": "input", "style": "width:100%;"}),
            "vive_junto": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "es_responsable": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "notas": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "Notas breves sobre este familiar (opcional)",
                    "class": "textarea",
                }
            ),
        }

class EnviarFichaMiembroEmailForm(forms.Form):
    destinatario = forms.EmailField(
        label="Correo de destino",
        help_text="Correo al que se enviará este mensaje."
    )
    asunto = forms.CharField(
        label="Asunto",
        max_length=150
    )
    mensaje = forms.CharField(
        label="Mensaje",
        widget=forms.Textarea,
        required=False,
        help_text="Mensaje opcional que se incluirá en el correo."
    )
    adjunto = forms.FileField(
        label="Adjuntar PDF",
        required=False,
        help_text="Opcional: selecciona un archivo PDF para adjuntar."
    )