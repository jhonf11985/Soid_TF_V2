from django import forms
from .models import EvaluacionMiembro, EvaluacionPerfilUnidad


class EvaluacionPerfilUnidadForm(forms.ModelForm):
    class Meta:
        model = EvaluacionPerfilUnidad
        fields = [
            "modo",
            "frecuencia",
            "dia_cierre",
            "auto_crear_periodo",
            "permitir_editar_cerrada",
            "excluir_evaluador",

            "usar_asistencia",
            "usar_participacion",
            "usar_compromiso",
            "usar_actitud",
            "usar_integracion",
            "usar_madurez_espiritual",
            "usar_estado_espiritual",

            "w_asistencia",
            "w_participacion",
            "w_compromiso",
            "w_actitud",
            "w_integracion",
            "w_madurez_espiritual",
        ]
        widgets = {
            "dia_cierre": forms.NumberInput(attrs={"min": 1, "max": 28}),
        }


class EvaluacionMiembroForm(forms.ModelForm):
    class Meta:
        model = EvaluacionMiembro
        fields = (
            "asistencia",
            "participacion",
            "compromiso",
            "actitud",
            "integracion",
            "madurez_espiritual",
            "estado_espiritual",
            "observacion",
        )
        widgets = {
            "observacion": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Observación opcional (máx. 255)."
            }),
        }
