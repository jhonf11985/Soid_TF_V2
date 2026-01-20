from django import forms
from .models import Recurso, CategoriaRecurso, Ubicacion


class RecursoForm(forms.ModelForm):
    class Meta:
        model = Recurso
        fields = [
            # Básico
            "codigo",
            "nombre",
            "categoria",
            "ubicacion",
            "estado",
            "cantidad_total",
            "foto",

            # Prioridad 1
            "marca",
            "modelo",
            "numero_serie",

            # Prioridad 2
            "condicion_fisica",
            "es_consumible",
            "requiere_mantenimiento",

            # Prioridad 3
            "fecha_compra",
            "proveedor",
            "costo_unitario",
            "garantia_hasta",
            # Depreciación
            "deprecia",
            "metodo_depreciacion",
            "vida_util_anios",
            "valor_residual_unitario",
            "fecha_inicio_depreciacion",

            # Notas
            "descripcion",
        ]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "fecha_compra": forms.DateInput(attrs={"type": "date"}),
            "garantia_hasta": forms.DateInput(attrs={"type": "date"}),
            "fecha_inicio_depreciacion": forms.DateInput(attrs={"type": "date"}),

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Clases mínimas (sin tocar tu CSS global)
        for name, field in self.fields.items():
            widget = field.widget
            classes = widget.attrs.get("class", "")
            if isinstance(widget, (forms.TextInput, forms.NumberInput, forms.Select, forms.ClearableFileInput, forms.Textarea, forms.DateInput)):
                widget.attrs["class"] = (classes + " odoo-input").strip()

        # Placeholders útiles
        self.fields["codigo"].widget.attrs.setdefault("placeholder", "INV-0001")
        self.fields["nombre"].widget.attrs.setdefault("placeholder", "Ej: Micrófono inalámbrico Shure")
        self.fields["marca"].widget.attrs.setdefault("placeholder", "Ej: Shure, Yamaha, JBL…")
        self.fields["modelo"].widget.attrs.setdefault("placeholder", "Ej: SM58, MG10XU…")
        self.fields["numero_serie"].widget.attrs.setdefault("placeholder", "Ej: SN-123456")
        self.fields["proveedor"].widget.attrs.setdefault("placeholder", "Ej: Tienda X / Donación / Ferretería…")

        self.fields["cantidad_total"].widget.attrs.setdefault("min", 1)


class CategoriaRecursoForm(forms.ModelForm):
    class Meta:
        model = CategoriaRecurso
        fields = ["nombre", "descripcion", "activo"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            widget = field.widget
            classes = widget.attrs.get("class", "")
            if name != "activo":
                widget.attrs["class"] = (classes + " odoo-input").strip()

        self.fields["nombre"].widget.attrs.setdefault("placeholder", "Ej: Audio y sonido")


class UbicacionForm(forms.ModelForm):
    class Meta:
        model = Ubicacion
        fields = ["nombre", "descripcion"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            widget = field.widget
            classes = widget.attrs.get("class", "")
            widget.attrs["class"] = (classes + " odoo-input").strip()

        self.fields["nombre"].widget.attrs.setdefault("placeholder", "Ej: Salón principal, Bodega, Oficina pastoral")
