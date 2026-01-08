from django import forms
from .models import SolicitudActualizacionMiembro, SolicitudAltaMiembro
from miembros_app.models import GENERO_CHOICES, ESTADO_MIEMBRO_CHOICES


class SolicitudActualizacionForm(forms.ModelForm):
    class Meta:
        model = SolicitudActualizacionMiembro
        fields = [
            "telefono", "whatsapp", "email",
            "direccion", "sector", "ciudad", "provincia", "codigo_postal",
            "empleador", "puesto", "telefono_trabajo", "direccion_trabajo",
            "contacto_emergencia_nombre", "contacto_emergencia_telefono", "contacto_emergencia_relacion",
            "tipo_sangre", "alergias", "condiciones_medicas", "medicamentos",
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
