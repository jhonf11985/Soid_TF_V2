from django import forms
from .models import MovimientoFinanciero, CategoriaMovimiento, CuentaFinanciera
from miembros_app.models import Miembro  # 👈 IMPORTAMOS MIEMBRO
from django.apps import apps
from django.db.models import Q  # Añadir este import
def is_module_enabled(*codes: str) -> bool:
    """
    Verifica si existe un Module (normalmente core.Module) habilitado.
    - Soporta varios codes.
    - Compara sin importar mayúsculas/minúsculas (iexact).
    - Falla seguro devolviendo False.
    """
    ModuleModel = None

    # 1) Caso típico: core.Module
    try:
        ModuleModel = apps.get_model("core", "Module")
    except Exception:
        ModuleModel = None

    # 2) Fallback: buscar cualquier modelo llamado Module con campos code/is_enabled
    if ModuleModel is None:
        try:
            for m in apps.get_models():
                if m.__name__ == "Module":
                    field_names = {f.name for f in m._meta.fields}
                    if "code" in field_names and "is_enabled" in field_names:
                        ModuleModel = m
                        break
        except Exception:
            ModuleModel = None

    if ModuleModel is None:
        return False

    try:
        q = Q()
        for c in codes:
            q |= Q(code__iexact=c)
        return ModuleModel.objects.filter(is_enabled=True).filter(q).exists()
    except Exception:
        return False

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
            "unidad",
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

        # --------------------------------------------
        # UNIDAD (solo si Estructura está activa)
        # --------------------------------------------
        estructura_activa = is_module_enabled("Estructura", "Unidad", "Unidades")

        if not estructura_activa:
            # Si estructura no está activa, quitamos el campo
            self.fields.pop("unidad", None)
        else:
            try:
                Unidad = apps.get_model("estructura_app", "Unidad")

                # ✅ Solo unidades activas y visibles (como se espera en UI)
                self.fields["unidad"].queryset = (
                    Unidad.objects
                    .filter(activa=True, visible=True)
                    .order_by("orden", "nombre")
                )

                self.fields["unidad"].required = False
                self.fields["unidad"].label = "Unidad"
                self.fields["unidad"].help_text = "Opcional."
            except Exception:
                # Si no existe el modelo o falla algo, lo ocultamos para evitar error
                self.fields.pop("unidad", None)

        # --------------------------------------------
        # REGLA: si es EDICIÓN de un ingreso confirmado,
        # solo se puede corregir lo NO contable.
        # --------------------------------------------
        if self.instance and self.instance.pk:
            if self.instance.estado == "confirmado":
                campos_bloqueados = ["fecha", "cuenta", "categoria", "monto", "forma_pago"]
                for name in campos_bloqueados:
                    if name in self.fields:
                        self.fields[name].disabled = True
                        self.fields[name].help_text = "Este campo no se puede modificar en un ingreso confirmado."

            if self.instance.estado == "anulado":
                # Si está anulado, bloqueamos todo (por seguridad).
                for f in self.fields.values():
                    f.disabled = True

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
              "unidad",
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
        # Filtrar categorías a solo tipo ingreso y activas
        self.fields["categoria"].queryset = CategoriaMovimiento.objects.filter(
            tipo="egreso",
            activo=True
        ).order_by("nombre")

        # Filtrar solo cuentas activas
        self.fields["cuenta"].queryset = CuentaFinanciera.objects.filter(
            esta_activa=True
        ).order_by("nombre")
        # --------------------------------------------
        # UNIDAD (solo si Estructura está activa)
        # --------------------------------------------
        estructura_activa = is_module_enabled("Estructura", "Unidad", "Unidades")

        if not estructura_activa:
            self.fields.pop("unidad", None)
        else:
            try:
                Unidad = apps.get_model("estructura_app", "Unidad")
                self.fields["unidad"].queryset = (
                    Unidad.objects
                    .filter(activa=True, visible=True)
                    .order_by("orden", "nombre")
                )
                self.fields["unidad"].required = False
                self.fields["unidad"].label = "Unidad"
                self.fields["unidad"].help_text = "Opcional."
            except Exception:
                self.fields.pop("unidad", None)

        # IMPORTANTE: El campo persona_asociada ahora se maneja con autocomplete
        # Ocultamos el widget por defecto y lo manejamos con JS
        if "persona_asociada" in self.fields:
            self.fields["persona_asociada"].widget = forms.HiddenInput()
            self.fields["persona_asociada"].required = False

# ============================================
# FORMULARIO DE TRANSFERENCIA
# ============================================

class TransferenciaForm(forms.Form):
    """
    Formulario para transferencias entre cuentas.
    No hereda de ModelForm porque crea DOS movimientos a la vez.
    """
    fecha = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Fecha de transferencia"
    )
    
    cuenta_origen = forms.ModelChoiceField(
        queryset=CuentaFinanciera.objects.filter(esta_activa=True),
        label="De la cuenta",
        help_text="Cuenta desde donde sale el dinero"
    )
    
    cuenta_destino = forms.ModelChoiceField(
        queryset=CuentaFinanciera.objects.filter(esta_activa=True),
        label="A la cuenta",
        help_text="Cuenta donde entra el dinero"
    )
    
    monto = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01,
        label="Monto",
        widget=forms.NumberInput(attrs={
            "step": "0.01",
            "min": "0.01",
            "placeholder": "0.00"
        })
    )
    
    descripcion = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 2,
            "placeholder": "Motivo de la transferencia..."
        }),
        label="Descripción"
    )
    
    referencia = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Nº de operación, comprobante, etc."
        }),
        label="Referencia"
    )
    
    def clean(self):
        """
        Validaciones personalizadas.
        """
        cleaned_data = super().clean()
        cuenta_origen = cleaned_data.get("cuenta_origen")
        cuenta_destino = cleaned_data.get("cuenta_destino")
        
        # Validar que no sean la misma cuenta
        if cuenta_origen and cuenta_destino and cuenta_origen == cuenta_destino:
            raise forms.ValidationError(
                "No puedes transferir a la misma cuenta. Selecciona cuentas diferentes."
            )
        
        # Validar que sean de la misma moneda (por ahora)
        if cuenta_origen and cuenta_destino:
            if cuenta_origen.moneda != cuenta_destino.moneda:
                raise forms.ValidationError(
                    f"Las cuentas deben ser de la misma moneda. "
                    f"Origen: {cuenta_origen.moneda}, Destino: {cuenta_destino.moneda}."
                )
        
        return cleaned_data
    
