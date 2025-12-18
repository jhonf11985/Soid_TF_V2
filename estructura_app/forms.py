from django import forms
from .models import Unidad


class UnidadForm(forms.ModelForm):
    class Meta:
        model = Unidad
        fields = [
            "nombre",
            "categoria",
            
            "tipo",
            "padre",
            "descripcion",
            "codigo",
            "orden",
            "notas",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "odoo-name-input",
                "placeholder": "Nombre de la unidad",
                "autocomplete": "off",
            }),
            "categoria": forms.Select(attrs={"class": "odoo-input"}),
            
            "tipo": forms.Select(attrs={"class": "odoo-input"}),
            "padre": forms.Select(attrs={"class": "odoo-input"}),
            "descripcion": forms.Textarea(attrs={
                "class": "odoo-textarea",
                "rows": 4,
                "placeholder": "Descripción breve de la unidad...",
            }),
            "codigo": forms.TextInput(attrs={"class": "odoo-input", "placeholder": "Ej. JUV-01"}),
            "orden": forms.NumberInput(attrs={"class": "odoo-input", "min": 0}),
            "notas": forms.Textarea(attrs={"class": "odoo-textarea", "rows": 4, "placeholder": "Notas internas..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ Tipo (FK) solo activos
        self.fields["tipo"].queryset = self.fields["tipo"].queryset.filter(activo=True)
        self.fields["tipo"].empty_label = None

        # ✅ Categoría (FK) solo activas
        self.fields["categoria"].queryset = self.fields["categoria"].queryset.filter(activo=True)
        self.fields["categoria"].empty_label = None

        # ✅ Defaults al crear (si existe al menos 1)
        if not self.instance.pk and not self.data.get("tipo"):
            first_tipo = self.fields["tipo"].queryset.order_by("orden", "nombre").first()
            if first_tipo:
                self.fields["tipo"].initial = first_tipo.pk

        if not self.instance.pk and not self.data.get("categoria"):
            first_cat = self.fields["categoria"].queryset.order_by("orden", "nombre").first()
            if first_cat:
                self.fields["categoria"].initial = first_cat.pk

        # Padre opcional
        self.fields["padre"].required = False
