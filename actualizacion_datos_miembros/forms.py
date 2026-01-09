from django import forms
from .models import SolicitudActualizacionMiembro, SolicitudAltaMiembro
from miembros_app.models import GENERO_CHOICES, ESTADO_MIEMBRO_CHOICES




from django import forms
from .models import SolicitudActualizacionMiembro, SolicitudAltaMiembro


class SolicitudActualizacionForm(forms.ModelForm):
    """
    Formulario público para actualización de datos.
    Permite recortar campos dinámicamente con allowed_fields.
    """

    def __init__(self, *args, **kwargs):
        # Lista de campos permitidos decidida por admin/config.
        # Si viene None o vacía, se muestran todos los del Meta.fields.
        allowed_fields = kwargs.pop("allowed_fields", None)
        super().__init__(*args, **kwargs)

        # Si el admin decide campos, eliminamos los demás del formulario
        if allowed_fields:
            allowed = set(allowed_fields)
            for name in list(self.fields.keys()):
                if name not in allowed:
                    self.fields.pop(name)

        # Guardamos para la plantilla si lo quieres mostrar/debug
        self.allowed_fields = list(self.fields.keys())
  # ===============================
    # Normalización de pasaporte
    # ===============================
    def clean_pasaporte(self):
        pasaporte = (self.cleaned_data.get("pasaporte") or "").strip()

        if not pasaporte:
            return ""

        # Quitar espacios y guiones
        pasaporte = re.sub(r"[\s-]+", "", pasaporte)

        # Solo letras y números
        pasaporte = re.sub(r"[^A-Za-z0-9]", "", pasaporte)

        # Mayúsculas
        pasaporte = pasaporte.upper()

        # Validación suave (no agresiva)
        if not (6 <= len(pasaporte) <= 15):
            raise forms.ValidationError(
                "Pasaporte inválido. Usa solo letras y números (6 a 15 caracteres)."
            )

        return pasaporte
    def clean_telefono_secundario(self):
        raw = (self.cleaned_data.get("telefono_secundario") or "").strip()

        if not raw:
            return ""

        digits = "".join(c for c in raw if c.isdigit())

        if len(digits) == 10 and digits.startswith(("809", "829", "849")):
            return "+1" + digits

        if len(digits) == 11 and digits.startswith("1"):
            if digits[1:4] in ("809", "829", "849"):
                return "+" + digits

        raise forms.ValidationError(
            "Teléfono secundario inválido. Ejemplo: 8091234567."
        )

    class Meta:
        model = SolicitudActualizacionMiembro
        fields = [
            "telefono", "whatsapp", "email",
            "direccion", "sector", "ciudad", "provincia", "codigo_postal",
            "empleador", "puesto", "telefono_trabajo", "direccion_trabajo",
            "contacto_emergencia_nombre", "contacto_emergencia_telefono", "contacto_emergencia_relacion",
            "tipo_sangre", "alergias", "condiciones_medicas", "medicamentos",
            "telefono_secundario",
                "lugar_nacimiento",
                "nacionalidad",
                "estado_civil",
                "nivel_educativo",
                "profesion",
                "pasaporte",
        ]
        widgets = {
            "direccion": forms.Textarea(attrs={"rows": 2}),
            "direccion_trabajo": forms.Textarea(attrs={"rows": 2}),
            "alergias": forms.Textarea(attrs={"rows": 2}),
            "condiciones_medicas": forms.Textarea(attrs={"rows": 2}),
            "medicamentos": forms.Textarea(attrs={"rows": 2}),
        }


class SolicitudAltaPublicaForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ⛔ TEMPORALMENTE DESACTIVADO
        # Antes se permitía seleccionar el estado del miembro desde el formulario.
        # Ahora el estado se asigna automáticamente como "activo" al guardar.
        #
        # self.fields["estado_miembro"].choices = [
        #     (value, label)
        #     for value, label in ESTADO_MIEMBRO_CHOICES
        #     if value != "descarriado"
        # ]

    # ===============================
    # Normalización de teléfonos RD
    # ===============================
    def _normalizar_rd_a_e164(self, raw: str, requerido: bool, campo: str) -> str:
        raw = (raw or "").strip()

        if not raw:
            if requerido:
                raise forms.ValidationError(f"El campo {campo} es obligatorio.")
            return ""

        digits = "".join(c for c in raw if c.isdigit())

        if len(digits) == 10 and digits.startswith(("809", "829", "849")):
            return "+1" + digits

        if len(digits) == 11 and digits.startswith("1"):
            if digits[1:4] in ("809", "829", "849"):
                return "+" + digits

        if raw.startswith("+") and len(digits) == 11 and digits.startswith("1"):
            if digits[1:4] in ("809", "829", "849"):
                return "+" + digits

        raise forms.ValidationError(
            f"{campo} inválido para RD. Ejemplo: 8091234567."
        )

    def clean_nombres(self):
        return (self.cleaned_data.get("nombres") or "").strip()

    def clean_apellidos(self):
        return (self.cleaned_data.get("apellidos") or "").strip()

    def clean_telefono(self):
        return self._normalizar_rd_a_e164(
            self.cleaned_data.get("telefono"),
            requerido=True,
            campo="Teléfono",
        )

    def clean_whatsapp(self):
        return self._normalizar_rd_a_e164(
            self.cleaned_data.get("whatsapp"),
            requerido=False,
            campo="WhatsApp",
        )

    # ===============================
    # Guardado con estado por defecto
    # ===============================
    def save(self, commit=True):
        instance = super().save(commit=False)

        # ⛔ CAMPO NO USADO EN FORMULARIO
        # El estado del miembro se asigna automáticamente.
        # Si en el futuro se quiere validar o cambiar la lógica,
        # este es el punto correcto.
        instance.estado_miembro = "activo"

        if commit:
            instance.save()

        return instance

    class Meta:
        model = SolicitudAltaMiembro

        # ⛔ estado_miembro COMENTADO
        # No se expone en el formulario público
        fields = [
            "nombres",
            "apellidos",
            "genero",
            "fecha_nacimiento",
            # "estado_miembro",
            "telefono",
            "whatsapp",
            "direccion",
            "sector",
            "cedula",
            "foto",
        ]

        widgets = {
            "nombres": forms.TextInput(attrs={
                "class": "odoo-input",
                "placeholder": "Nombres"
            }),
            "apellidos": forms.TextInput(attrs={
                "class": "odoo-input",
                "placeholder": "Apellidos"
            }),
            "genero": forms.Select(attrs={
                "class": "odoo-input odoo-select"
            }),
            "fecha_nacimiento": forms.DateInput(attrs={
                "class": "odoo-input",
                "type": "date"
            }),

            # ⛔ Widget comentado (no se usa por ahora)
            # "estado_miembro": forms.Select(attrs={
            #     "class": "odoo-input odoo-select"
            # }),

            "telefono": forms.TextInput(attrs={
                "class": "odoo-input",
                "placeholder": "809-123-4567",
                "inputmode": "numeric",
                "autocomplete": "tel",
            }),
            "whatsapp": forms.TextInput(attrs={
                "class": "odoo-input",
                "placeholder": "+18091234567",
                "readonly": "readonly",
                "tabindex": "-1",
            }),
            "cedula": forms.TextInput(attrs={
                "class": "odoo-input",
                "placeholder": "Cédula (opcional)",
                "inputmode": "numeric",
            }),
            "foto": forms.ClearableFileInput(attrs={
                "class": "odoo-input",
                "accept": "image/*",
            }),
            "direccion": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": "Dirección (opcional)"
            }),
            "sector": forms.TextInput(attrs={
                "class": "odoo-input",
                "placeholder": "Sector (opcional)"
            }),
        }




class ActualizacionDatosConfigForm(forms.Form):
    activo = forms.BooleanField(required=False, initial=True, label="Formulario público activo")

    campos_permitidos = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[],
        label="Campos a solicitar (público)"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Lista de campos permitidos (debe coincidir con SolicitudActualizacionForm.Meta.fields)
        self.fields["campos_permitidos"].choices = [
            ("telefono", "Teléfono"),
            ("whatsapp", "WhatsApp"),
            ("email", "Email"),

            ("direccion", "Dirección"),
            ("sector", "Sector"),
            ("ciudad", "Ciudad"),
            ("provincia", "Provincia"),
            ("codigo_postal", "Código postal"),

            ("empleador", "Empleador"),
            ("puesto", "Puesto"),
            ("telefono_trabajo", "Teléfono trabajo"),
            ("direccion_trabajo", "Dirección trabajo"),

            ("contacto_emergencia_nombre", "Contacto emergencia (Nombre)"),
            ("contacto_emergencia_telefono", "Contacto emergencia (Teléfono)"),
            ("contacto_emergencia_relacion", "Contacto emergencia (Relación)"),

            ("tipo_sangre", "Tipo de sangre"),
            ("alergias", "Alergias"),
            ("condiciones_medicas", "Condiciones médicas"),
            ("medicamentos", "Medicamentos"),
            ("telefono_secundario", "Teléfono secundario"),
            ("lugar_nacimiento", "Lugar de nacimiento"),
            ("nacionalidad", "Nacionalidad"),
            ("estado_civil", "Estado civil"),
            ("nivel_educativo", "Nivel educativo"),
            ("profesion", "Profesión"),
            ("pasaporte", "Pasaporte"),
        ]
