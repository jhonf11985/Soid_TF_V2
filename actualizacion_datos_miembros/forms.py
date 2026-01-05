from django import forms
from .models import SolicitudActualizacionMiembro


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
