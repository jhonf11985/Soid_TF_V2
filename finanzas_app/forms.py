from django import forms
from .models import MovimientoFinanciero, CategoriaMovimiento, CuentaFinanciera
from miembros_app.models import Miembro  # 👈 IMPORTAMOS MIEMBRO


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
            "es_editable",
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
# FORMULARIO GENERAL DE MOVIMIENTO
# (para usos genéricos / edición rápida)
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
            "forma_pago",
            "persona_asociada",
            "descripcion",
            "referencia",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "descripcion": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": "Notas adicionales...",
            }),
            "referencia": forms.TextInput(attrs={
                "placeholder": "Nº recibo, factura, transferencia, etc.",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cargar miembros activos ordenados por nombre y apellidos
        if "persona_asociada" in self.fields:
            self.fields["persona_asociada"].queryset = Miembro.objects.filter(
                activo=True
            ).order_by("nombres", "apellidos")


# ============================================
# FORMULARIO DE INGRESO
# ============================================

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

        # Cargar miembros activos para el select de persona_asociada
        if "persona_asociada" in self.fields:
            self.fields["persona_asociada"].queryset = Miembro.objects.filter(
                activo=True
            ).order_by("nombres", "apellidos")
            self.fields["persona_asociada"].required = False


# ============================================
# FORMULARIO DE EGRESO
# ============================================

class MovimientoEgresoForm(forms.ModelForm):
    """
    Formulario especializado solo para EGRESOS.
    Igual al de ingresos, pero filtrando categorías tipo egreso.
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
            "descripcion": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": "Motivo del egreso, notas adicionales...",
            }),
            "referencia": forms.TextInput(attrs={
                "placeholder": "Nº factura, cheque, transferencia, etc.",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = CategoriaMovimiento.objects.filter(
            tipo="egreso",
            activo=True
        ).order_by("nombre")
        self.fields["cuenta"].queryset = CuentaFinanciera.objects.filter(
            esta_activa=True
        ).order_by("nombre")

        # Cargar miembros activos para el select de persona_asociada
        if "persona_asociada" in self.fields:
            self.fields["persona_asociada"].queryset = Miembro.objects.filter(
                activo=True
            ).order_by("nombres", "apellidos")
            self.fields["persona_asociada"].required = False
