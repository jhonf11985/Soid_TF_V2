from django import forms
from .models import NuevoCreyenteExpediente


class NuevoCreyenteExpedienteForm(forms.ModelForm):
    class Meta:
        model = NuevoCreyenteExpediente
        fields = ["responsable", "proximo_contacto", "notas"]
        widgets = {
            "responsable": forms.Select(attrs={"class": "input"}),
            "proximo_contacto": forms.DateInput(attrs={"class": "input", "type": "date"}),
            "notas": forms.Textarea(attrs={"class": "input", "rows": 5, "placeholder": "Escribe notas del seguimiento..."}),
        }
