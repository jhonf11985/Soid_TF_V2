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
            "regla_ganador",
            "numero_cargos",
            "edad_minima_candidato",
            "total_habilitados",        # auto
            "miembros_presentes",       # manual
            "tipo_quorum",
            "valor_quorum",
            "votos_minimos_requeridos", # auto
            "fecha_inicio",
            "fecha_fin",
            "permite_empates",
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
            "tipo": forms.Select(),
            "estado": forms.Select(),
            "regla_ganador": forms.Select(),
            "numero_cargos": forms.NumberInput(attrs={
                "placeholder": "Ej.: 3"
            }),
            "edad_minima_candidato": forms.NumberInput(attrs={
                "placeholder": "Ej.: 18"
            }),

            "total_habilitados": forms.NumberInput(attrs={
                "placeholder": "Calculado automáticamente",
            }),
            "miembros_presentes": forms.NumberInput(attrs={
                "placeholder": "Ej.: 80 presentes",
            }),
            "tipo_quorum": forms.Select(),
            "valor_quorum": forms.NumberInput(attrs={
                "placeholder": "Ej.: 50 (porcentaje) o 80 (cantidad fija)",
            }),
            "votos_minimos_requeridos": forms.NumberInput(attrs={
                "placeholder": "Se calculará automáticamente",
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

            "permite_empates": forms.CheckboxInput(),
            "permite_voto_remoto": forms.CheckboxInput(),

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

        # Campos automáticos (solo lectura en el formulario)
        if "total_habilitados" in self.fields:
            self.fields["total_habilitados"].widget.attrs["readonly"] = "readonly"
        if "votos_minimos_requeridos" in self.fields:
            self.fields["votos_minimos_requeridos"].widget.attrs["readonly"] = "readonly"
