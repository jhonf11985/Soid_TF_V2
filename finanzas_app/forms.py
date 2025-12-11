# finanzas_app/forms.py
from django import forms
from .models import MovimientoFinanciero, CategoriaMovimiento, CuentaFinanciera


# ============================================
# FORMULARIO DE CUENTA FINANCIERA
# ============================================

class CuentaFinancieraForm(forms.ModelForm):
    class Meta:
        model = CuentaFinanciera
        fields = [
            "nombre",
            "tipo",
            "moneda",
            "saldo_inicial",
            "descripcion",
            "esta_activa",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej: Caja general, Banco Popular...",
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": "Descripción opcional de la cuenta...",
            }),
            "saldo_inicial": forms.NumberInput(attrs={
                "step": "0.01",
                "min": "0",
                "placeholder": "0.00",
            }),
        }


# ============================================
# FORMULARIO DE CATEGORÍA DE MOVIMIENTO
# ============================================

class CategoriaMovimientoForm(forms.ModelForm):
    class Meta:
        model = CategoriaMovimiento
        fields = [
            "nombre",
            "tipo",
            "descripcion",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej: Diezmo, Ofrenda, Mantenimiento...",
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": "Descripción opcional...",
            }),
        }
        labels = {
            "tipo": "Tipo de categoría",
            "activo": "Categoría activa",
        }


# ============================================
# FORMULARIOS DE MOVIMIENTOS
# ============================================

class MovimientoFinancieroForm(forms.ModelForm):
    class Meta:
        model = CuentaFinanciera
        fields = [
            "nombre",
            "tipo",
            "moneda",
            "saldo_inicial",
            "descripcion",
            "esta_activa",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ej: Caja general, Banco Popular...",
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": "Descripción opcional de la cuenta...",
            }),
            "saldo_inicial": forms.NumberInput(attrs={
                "step": "0.01",
                "min": "0",
                "placeholder": "0.00",
            }),
        }


# ============================================
# FORMULARIOS DE MOVIMIENTOS
# ============================================

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
            "forma_pago",
            "persona_asociada",
            "descripcion",
            "referencia",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "persona_asociada": forms.TextInput(attrs={
                "placeholder": "Nombre de quien entrega (opcional)",
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": "Notas adicionales...",
            }),
            "referencia": forms.TextInput(attrs={
                "placeholder": "Nº transferencia, cheque, etc.",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar categorías a solo tipo ingreso y activas
        self.fields["categoria"].queryset = CategoriaMovimiento.objects.filter(
            tipo="ingreso",
            activo=True
        ).order_by("nombre")
        
        # Filtrar solo cuentas activas
        self.fields["cuenta"].queryset = CuentaFinanciera.objects.filter(
            esta_activa=True
        ).order_by("nombre")