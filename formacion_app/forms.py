from django import forms
from .models import ProgramaEducativo


class ProgramaEducativoForm(forms.ModelForm):
    class Meta:
        model = ProgramaEducativo
        fields = [
            "nombre",
            "descripcion",
            "tipo",
            "activo",
        ]

from .models import CicloPrograma



class CicloProgramaForm(forms.ModelForm):
    class Meta:
        model = CicloPrograma
        fields = [
            "programa",
            "nombre",
            "fecha_inicio",
            "fecha_fin",
            "activo",
        ]
        labels = {
            "programa": "Programa educativo",
            "nombre": "Nombre del ciclo",
            "fecha_inicio": "Fecha de inicio",
            "fecha_fin": "Fecha de finalización",
            "activo": "Activo",
        }
        widgets = {
            "programa": forms.Select(attrs={
                "class": "form-select"
            }),
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: 2026, Trimestre 1 - 2026"
            }),
            "fecha_inicio": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
            "fecha_fin": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
            "activo": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }