from django import forms
from .models import EvaluacionMiembro


class EvaluacionMiembroForm(forms.ModelForm):
    class Meta:
        model = EvaluacionMiembro
        fields = ('asistencia', 'participacion', 'estado', 'observacion')
        widgets = {
            'observacion': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Observación opcional (máx. 255).'
            }),
        }
