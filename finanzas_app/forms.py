# finanzas_app/forms.py
from django import forms
from .models import MovimientoFinanciero, CategoriaMovimiento


class MovimientoFinancieroForm(forms.ModelForm):
    class Meta:
        model = MovimientoFinanciero
        fields = [
            "fecha",
            "tipo",
            "cuenta",
            "categoria",
            "monto",
            "descripcion",
            "referencia",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
        }

class MovimientoFinancieroForm(forms.ModelForm):
    class Meta:
        model = MovimientoFinanciero
        fields = [
            "fecha",
            "tipo",
            "cuenta",
            "categoria",
            "monto",
            "descripcion",
            "referencia",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
        }


class MovimientoIngresoForm(forms.ModelForm):
    """
    Formulario especializado solo para INGRESOS.
    No muestra el campo 'tipo' y filtra las categorías a solo ingresos.
    """

    class Meta:
        model = MovimientoFinanciero
        fields = [
            "fecha",
            "cuenta",
            "categoria",
            "monto",
            "descripcion",
            "referencia",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar categorías a solo tipo ingreso y activas
        self.fields["categoria"].queryset = CategoriaMovimiento.objects.filter(
            tipo="ingreso",
            activo=True
        ).order_by("nombre")