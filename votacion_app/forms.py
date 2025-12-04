from django import forms
from .models import Votacion


class VotacionForm(forms.ModelForm):
    class Meta:
        model = Votacion
        fields = [
            "nombre",
            "descripcion",
            "tipo",
            "estado",
            "total_habilitados",
            "quorum_minimo",
            "regla_ganador",
            "numero_cargos",
            "edad_minima_candidato",
            "permite_empates",
            "fecha_inicio",
            "fecha_fin",
            "permite_voto_remoto",
            "observaciones_internas",
        ]

        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej.: Elección de diáconos 2026"
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Describa brevemente esta votación…"
            }),
            "tipo": forms.Select(attrs={
                "placeholder": "Seleccione el tipo de votación"
            }),
            "estado": forms.Select(attrs={
                "placeholder": "Seleccione el estado"
            }),
            "total_habilitados": forms.NumberInput(attrs={
                "placeholder": "Ej.: 120"
            }),
            "quorum_minimo": forms.NumberInput(attrs={
                "placeholder": "Ej.: 80 (opcional)"
            }),
            "regla_ganador": forms.Select(attrs={
                "placeholder": "Seleccione la regla de ganador"
            }),
            "numero_cargos": forms.NumberInput(attrs={
                "placeholder": "Ej.: 3"
            }),
            "permite_empates": forms.CheckboxInput(),
            "permite_voto_remoto": forms.CheckboxInput(),

            "edad_minima_candidato": forms.NumberInput(attrs={
                "placeholder": "Ej.: 18"
            }),


            # DATETIME
            "fecha_inicio": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "placeholder": "Seleccione fecha/hora",
                },
                format="%Y-%m-%dT%H:%M"
            ),
            "fecha_fin": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "placeholder": "Seleccione fecha/hora",
                },
                format="%Y-%m-%dT%H:%M"
            ),

            "observaciones_internas": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Notas internas sobre esta votación…"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Prellenar datetime-local al editar
        for campo in ["fecha_inicio", "fecha_fin"]:
            valor = getattr(self.instance, campo)
            if valor:
                self.initial[campo] = valor.strftime("%Y-%m-%dT%H:%M")
