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
        fields = "__all__"
