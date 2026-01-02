from django import forms
from .models import NuevoCreyenteExpediente


from estructura_app.models import Unidad


class NuevoCreyenteExpedienteForm(forms.ModelForm):
    class Meta:
        model = NuevoCreyenteExpediente
        fields = [
            "etapa",
            "unidad_responsable",
            "responsable",
            "proximo_contacto",
            "notas",
        ]
        widgets = {
            "etapa": forms.Select(attrs={"class": "input"}),
            "unidad_responsable": forms.Select(attrs={"class": "input"}),
            "responsable": forms.Select(attrs={"class": "input"}),
            "proximo_contacto": forms.DateInput(attrs={"class": "input", "type": "date"}),
            "notas": forms.Textarea(attrs={"class": "input", "rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Solo unidades activas y visibles
        self.fields["unidad_responsable"].queryset = (
            Unidad.objects.filter(activa=True, visible=True).order_by("nombre")
        )
