from django import forms

from .models import (
    Visita,
    ClasificacionVisita,
    RegistroVisitas,
    TipoRegistroVisita,
)


class RegistroVisitasForm(forms.ModelForm):
    class Meta:
        model = RegistroVisitas
        fields = [
            "fecha",
            "tipo",
            "unidad_responsable",
            "observaciones",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "tipo": forms.Select(attrs={
                "class": "form-select",
            }),
            "unidad_responsable": forms.Select(attrs={
                "class": "form-select",
            }),
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Observaciones generales del registro",
            }),
        }

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)

        self.fields["observaciones"].required = False
        self.fields["unidad_responsable"].required = False

        if tenant is not None:
            self.fields["tipo"].queryset = TipoRegistroVisita.objects.filter(
                tenant=tenant,
                activo=True
            ).order_by("orden", "nombre")
        else:
            self.fields["tipo"].queryset = TipoRegistroVisita.objects.none()

        self.fields["tipo"].empty_label = "Seleccione un tipo"
        self.fields["unidad_responsable"].empty_label = "Seleccione una unidad"


class VisitaForm(forms.ModelForm):
    class Meta:
        model = Visita
        fields = [
            "nombre",
            "telefono",
            "genero",
            "edad",
            "clasificacion",
            "invitado_por",
            "desea_contacto",
            "peticion_oracion",
            "notas",
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
            "notas": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Notas internas",
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
        self.fields["notas"].required = False

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