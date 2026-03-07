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


from django import forms

from documentos_app.models import Carpeta, Documento


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = [
            "titulo",
            "descripcion",
            "carpeta",
            "categoria",
            "archivo",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Título del documento"}),
            "descripcion": forms.Textarea(
                attrs={
                    "placeholder": "Descripción breve del documento",
                    "rows": 4,
                }
            ),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)

        if "carpeta" in self.fields:
            self.fields["carpeta"].queryset = Carpeta.objects.filter(
                tenant=tenant,
                activa=True,
            ).order_by("nombre")
            self.fields["carpeta"].required = False

        if "categoria" in self.fields:
            categoria_field = self.fields["categoria"]
            if hasattr(categoria_field, "queryset"):
                categoria_field.queryset = categoria_field.queryset.filter(
                    tenant=tenant
                ).order_by("nombre")
            categoria_field.required = False

        for field_name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} form-control".strip()


from django import forms
from documentos_app.models import CategoriaDocumento


class CategoriaDocumentoForm(forms.ModelForm):
    class Meta:
        model = CategoriaDocumento
        fields = ["nombre", "descripcion"]

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} form-control".strip()