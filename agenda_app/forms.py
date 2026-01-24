from django import forms
from .models import Actividad


class ActividadForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = [
            "titulo",
            "fecha",
            "hora_inicio",
            "hora_fin",
            "tipo",
            "estado",
            "lugar",
            "responsable_texto",
            "descripcion",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date", "class": "odoo-input"}),
            "hora_inicio": forms.TimeInput(attrs={"type": "time", "class": "odoo-input"}),
            "hora_fin": forms.TimeInput(attrs={"type": "time", "class": "odoo-input"}),
            "titulo": forms.TextInput(attrs={"class": "odoo-input", "placeholder": "Ej: Culto de jóvenes"}),
            "lugar": forms.TextInput(attrs={"class": "odoo-input", "placeholder": "Ej: Santuario"}),
            "responsable_texto": forms.TextInput(attrs={"class": "odoo-input", "placeholder": "Ej: Ministerio de Jóvenes"}),
            "descripcion": forms.Textarea(attrs={"class": "odoo-input", "rows": 4, "placeholder": "Opcional"}),
            "tipo": forms.Select(attrs={"class": "odoo-input"}),
            "estado": forms.Select(attrs={"class": "odoo-input"}),
        }

    def clean(self):
        cleaned = super().clean()
        hi = cleaned.get("hora_inicio")
        hf = cleaned.get("hora_fin")
        if hi and hf and hf <= hi:
            self.add_error("hora_fin", "La hora fin debe ser mayor que la hora inicio.")
        return cleaned
