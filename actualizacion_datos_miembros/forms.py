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

    def _normalizar_rd_a_e164(self, raw: str, requerido: bool, campo: str) -> str:
        raw = (raw or "").strip()

        if not raw:
            if requerido:
                raise forms.ValidationError(f"El campo {campo} es obligatorio.")
            return ""

        digits = "".join(c for c in raw if c.isdigit())

        # Aceptar RD local: 10 dígitos empezando 809/829/849
        if len(digits) == 10 and digits.startswith(("809", "829", "849")):
            return "+1" + digits

        # Aceptar RD con código país sin "+"
        if len(digits) == 11 and digits.startswith("1"):
            if digits[1:4] in ("809", "829", "849"):
                return "+" + digits

        # Aceptar E.164 con +
        if raw.startswith("+") and len(digits) == 11 and digits.startswith("1"):
            if digits[1:4] in ("809", "829", "849"):
                return "+" + digits

        raise forms.ValidationError(
            f"{campo} inválido para RD. Ejemplo: 8091234567 (809/829/849)."
        )

    def clean_nombres(self):
        return (self.cleaned_data.get("nombres") or "").strip()

    def clean_apellidos(self):
        return (self.cleaned_data.get("apellidos") or "").strip()

    def clean_telefono(self):
        # Obligatorio + normalizado
        return self._normalizar_rd_a_e164(
            self.cleaned_data.get("telefono"),
            requerido=True,
            campo="Teléfono",
        )

    def clean_whatsapp(self):
        # Opcional + normalizado
        return self._normalizar_rd_a_e164(
            self.cleaned_data.get("whatsapp"),
            requerido=False,
            campo="WhatsApp",
        )

    class Meta:
        model = SolicitudAltaMiembro
        fields = [
            "nombres",
            "apellidos",
            "genero",
            "fecha_nacimiento",
            "estado_miembro",
            "telefono",
            "whatsapp",
            "direccion",
            "sector",
        ]
        widgets = {
            "nombres": forms.TextInput(attrs={"class": "odoo-input", "placeholder": "Nombres"}),
            "apellidos": forms.TextInput(attrs={"class": "odoo-input", "placeholder": "Apellidos"}),
            "genero": forms.Select(attrs={"class": "odoo-input odoo-select"}),
            "fecha_nacimiento": forms.DateInput(attrs={"class": "odoo-input", "type": "date"}),
            "estado_miembro": forms.Select(attrs={"class": "odoo-input odoo-select"}),

            "telefono": forms.TextInput(attrs={
                "class": "odoo-input",
                "placeholder": "809-123-4567",
                "inputmode": "numeric",
                "autocomplete": "tel",
            }),
            "whatsapp": forms.TextInput(attrs={
                "class": "odoo-input",
                "placeholder": "809-123-4567 (opcional)",
                "inputmode": "numeric",
                "autocomplete": "tel",
            }),
            "direccion": forms.Textarea(attrs={"rows": 2, "placeholder": "Dirección (opcional)"}),
            "sector": forms.TextInput(attrs={"class": "odoo-input", "placeholder": "Sector (opcional)"}),
        }