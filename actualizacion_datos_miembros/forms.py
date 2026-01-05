from django import forms
from .models import SolicitudActualizacionMiembro
from django import forms
from miembros_app.models import Miembro, GENERO_CHOICES, ESTADO_MIEMBRO_CHOICES

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



class PublicRegistroAltaForm(forms.Form):
    nombres = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={"class": "odoo-input", "placeholder": "Nombres"})
    )
    apellidos = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={"class": "odoo-input", "placeholder": "Apellidos"})
    )

    genero = forms.ChoiceField(
        choices=[("", "Seleccione...")] + list(GENERO_CHOICES),
        required=True,
        widget=forms.Select(attrs={"class": "odoo-input odoo-select"})
    )

    fecha_nacimiento = forms.DateField(
        required=True,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"class": "odoo-input", "type": "date"})
    )

    estado_miembro = forms.ChoiceField(
        choices=[("", "Seleccione...")] + list(ESTADO_MIEMBRO_CHOICES),
        required=True,
        widget=forms.Select(attrs={"class": "odoo-input odoo-select"})
    )

    telefono = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={"class": "odoo-input", "placeholder": "Teléfono"})
    )

    def clean_nombres(self):
        return (self.cleaned_data["nombres"] or "").strip()

    def clean_apellidos(self):
        return (self.cleaned_data["apellidos"] or "").strip()

    def clean_telefono(self):
        return (self.cleaned_data["telefono"] or "").strip()
