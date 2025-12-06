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
            "base_quorum",              # base para el cálculo
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

            # Aunque en la plantilla uses tu propio <select>,
            # aquí dejamos el widget definido igualmente.
            "base_quorum": forms.Select(),

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

    def clean(self):
        cleaned = super().clean()

        tipo_quorum = cleaned.get("tipo_quorum")      # PORCENTAJE / CANTIDAD / None
        valor_quorum = cleaned.get("valor_quorum")    # número o None
        base_quorum = cleaned.get("base_quorum")      # HABILITADOS / PRESENTES / None
        miembros_presentes = cleaned.get("miembros_presentes")

        # Si no se ha definido ningún tipo, no forzamos nada
        if not tipo_quorum and not valor_quorum:
            return cleaned

        # 1) No permitir valor sin tipo
        if not tipo_quorum and valor_quorum is not None:
            self.add_error(
                "tipo_quorum",
                "Selecciona si el quórum se basa en porcentaje o en cantidad fija."
            )
            return cleaned

        # 2) No permitir tipo sin valor
        if tipo_quorum and valor_quorum is None:
            self.add_error(
                "valor_quorum",
                "Debes indicar el valor del quórum (porcentaje o cantidad)."
            )
            return cleaned

        # 3) Validaciones específicas por tipo
        if tipo_quorum == "PORCENTAJE" and valor_quorum is not None:
            # Debe estar entre 1 y 100
            if valor_quorum <= 0 or valor_quorum > 100:
                self.add_error(
                    "valor_quorum",
                    "El porcentaje de quórum debe estar entre 1 y 100."
                )

        if tipo_quorum == "CANTIDAD" and valor_quorum is not None:
            # Debe ser mayor que cero
            if valor_quorum <= 0:
                self.add_error(
                    "valor_quorum",
                    "La cantidad de quórum debe ser mayor que cero."
                )

            # Validación suave con miembros presentes (solo si ya los han puesto)
            if base_quorum == "PRESENTES" and miembros_presentes:
                if valor_quorum > miembros_presentes:
                    self.add_error(
                        "valor_quorum",
                            "La cantidad mínima de votos no puede ser mayor que los miembros presentes."
                    )

        return cleaned
