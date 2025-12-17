from django import forms
from .models import Unidad


class UnidadForm(forms.ModelForm):
    class Meta:
        model = Unidad
        fields = [
            "nombre",
            "categoria",
            "tipo_estructura",
            "tipo",
            "padre",
            "descripcion",
            "codigo",
            "orden",
            "visible",
            "activa",
            "fecha_cierre",
            "motivo_cierre",
            "notas",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "odoo-name-input",
                "placeholder": "Nombre de la unidad",
                "autocomplete": "off",
            }),
            "categoria": forms.Select(attrs={"class": "odoo-input"}),
            "tipo_estructura": forms.Select(attrs={"class": "odoo-input"}),
            "tipo": forms.Select(attrs={"class": "odoo-input"}),
            "padre": forms.Select(attrs={"class": "odoo-input"}),
            "descripcion": forms.Textarea(attrs={
                "class": "odoo-textarea",
                "rows": 4,
                "placeholder": "Descripción breve de la unidad...",
            }),
            "codigo": forms.TextInput(attrs={"class": "odoo-input", "placeholder": "Ej. JUV-01"}),
            "orden": forms.NumberInput(attrs={"class": "odoo-input", "min": 0}),
            "fecha_cierre": forms.DateInput(attrs={"class": "odoo-input", "type": "date"}),
            "motivo_cierre": forms.TextInput(attrs={"class": "odoo-input", "placeholder": "Motivo de cierre (si aplica)"}),
            "notas": forms.Textarea(attrs={"class": "odoo-textarea", "rows": 4, "placeholder": "Notas internas..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["activa"].required = False
        self.fields["visible"].required = False
