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
