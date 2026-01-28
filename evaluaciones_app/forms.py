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
                       "usar_liderazgo",
                       "usar_pesos",


            "w_asistencia",
            "w_participacion",
            "w_compromiso",
            "w_actitud",
            "w_integracion",
            "w_madurez_espiritual",
                       "w_liderazgo",
        ]
        widgets = {
            "dia_cierre": forms.NumberInput(attrs={"min": 1, "max": 28}),
        }


    def clean(self):
        cleaned_data = super().clean()

        pesos = [
            cleaned_data.get("w_asistencia", 0),
            cleaned_data.get("w_participacion", 0),
            cleaned_data.get("w_compromiso", 0),
            cleaned_data.get("w_actitud", 0),
            cleaned_data.get("w_integracion", 0),
            cleaned_data.get("w_madurez_espiritual", 0),
            cleaned_data.get("w_liderazgo", 0),
        ]

        total = sum(pesos)

        if total > 100:
            raise forms.ValidationError(
                f"La suma de los pesos no puede superar 100%. Actualmente es {total}%."
            )

        return cleaned_data
    


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
