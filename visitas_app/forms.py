from django import forms

from .models import Visita, ClasificacionVisita


class VisitaForm(forms.ModelForm):
    class Meta:
        model = Visita
        fields = [
            "nombre",
            "telefono",
            "genero",
            "edad",
            "clasificacion",
            "primera_vez",
            "invitado_por",
            "desea_contacto",
            "peticion_oracion",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre completo",
            }),
            "telefono": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Teléfono",
            }),
            "genero": forms.Select(attrs={
                "class": "form-select",
            }),
            "edad": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Edad",
                "min": "0",
            }),
            "clasificacion": forms.Select(attrs={
                "class": "form-select",
            }),
            "primera_vez": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
            "invitado_por": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Invitado por",
            }),
            "desea_contacto": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
            "peticion_oracion": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Petición de oración",
            }),
        }

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)

        self.fields["clasificacion"].required = False
        self.fields["telefono"].required = False
        self.fields["genero"].required = False
        self.fields["edad"].required = False
        self.fields["invitado_por"].required = False
        self.fields["peticion_oracion"].required = False

        if tenant is not None:
            self.fields["clasificacion"].queryset = ClasificacionVisita.objects.filter(
                tenant=tenant,
                activo=True
            ).order_by("nombre")
        else:
            self.fields["clasificacion"].queryset = ClasificacionVisita.objects.none()

        self.fields["clasificacion"].empty_label = "Seleccione una clasificación"

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        return nombre

    def clean_telefono(self):
        telefono = (self.cleaned_data.get("telefono") or "").strip()
        return telefono