from datetime import date

from django import forms
from .models import Miembro, MiembroRelacion

# Edad mínima para considerar a alguien bautizable como miembro oficial.
# Más adelante esto se puede leer desde parámetros configurables.
EDAD_MIN_BAUTISMO_POR_DEFECTO = 12


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
        ("descarriado", "Descarriado"),
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
        required=False,
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
            "categoria_miembro",   # <-- no se muestra
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
        edad_minima = EDAD_MIN_BAUTISMO_POR_DEFECTO

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

        return cleaned_data


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
