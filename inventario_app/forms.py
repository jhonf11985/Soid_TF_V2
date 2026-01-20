from django import forms
from .models import Recurso


class RecursoForm(forms.ModelForm):
    class Meta:
        model = Recurso
        fields = [
            "codigo",
            "nombre",
            "categoria",
            "ubicacion",
            "estado",
            "cantidad_total",
            "foto",
            "descripcion",
        ]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Clases mínimas (sin tocar tu CSS global)
        for name, field in self.fields.items():
            widget = field.widget
            classes = widget.attrs.get("class", "")
            if isinstance(widget, (forms.TextInput, forms.NumberInput, forms.Select, forms.ClearableFileInput, forms.Textarea)):
                widget.attrs["class"] = (classes + " odoo-input").strip()

        # Placeholders útiles
        if "codigo" in self.fields:
            self.fields["codigo"].widget.attrs.setdefault("placeholder", "INV-0001")
        if "nombre" in self.fields:
            self.fields["nombre"].widget.attrs.setdefault("placeholder", "Ej: Micrófono inalámbrico Shure")
        if "cantidad_total" in self.fields:
            self.fields["cantidad_total"].widget.attrs.setdefault("min", 1)
