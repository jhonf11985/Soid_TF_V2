from django import forms

from documentos_app.models import Carpeta


class CarpetaForm(forms.ModelForm):
    class Meta:
        model = Carpeta
        fields = ["nombre", "descripcion", "carpeta_padre"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: Actas, Finanzas, Recursos, Contratos"
            }),
            "descripcion": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Descripción breve de la carpeta"
            }),
            "carpeta_padre": forms.Select(attrs={
                "class": "form-control"
            }),
        }

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)

        if tenant is not None:
            self.fields["carpeta_padre"].queryset = Carpeta.objects.filter(
                tenant=tenant,
                activa=True,
            ).order_by("nombre")
        else:
            self.fields["carpeta_padre"].queryset = Carpeta.objects.none()

        self.fields["carpeta_padre"].required = False