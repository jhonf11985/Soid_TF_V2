from django import forms
from decimal import Decimal, InvalidOperation

from miembros_app.models import Miembro  # 👈 IMPORTAMOS MIEMBRO
from django.apps import apps
from django.db.models import Q  # Añadir este import
from .models import (
    MovimientoFinanciero,
    CategoriaMovimiento,
    CuentaFinanciera,
    ProveedorFinanciero,
    CuentaPorPagar,
)
import re
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Max


# ============================================
# WIDGET Y FIELD DE MONEDA CON PUNTO DECIMAL
# ============================================

class MonedaInput(forms.TextInput):
    """
    Widget de input para campos de moneda.
    Muestra el valor con formato de moneda (punto como decimal).
    """
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'moneda-input',
            'inputmode': 'decimal',
            'placeholder': '0.00',
            'autocomplete': 'off',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

    def format_value(self, value):
        """Formatea el valor para mostrar con punto decimal."""
        if value is None or value == '':
            return ''
        try:
            # Convertir a Decimal y formatear con 2 decimales
            decimal_value = Decimal(str(value))
            return f"{decimal_value:,.2f}".replace(',', 'X').replace('.', '.').replace('X', ',')
        except (InvalidOperation, ValueError):
            return str(value)


class MonedaField(forms.DecimalField):
    """
    Campo de formulario para moneda.
    Acepta entrada con comas como separador de miles y punto como decimal.
    """
    widget = MonedaInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_digits', 12)
        kwargs.setdefault('decimal_places', 2)
        kwargs.setdefault('min_value', Decimal('0'))
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        """Convierte el valor de entrada a Decimal."""
        if value in self.empty_values:
            return None
        
        # Limpiar el valor: quitar espacios y comas de miles
        value = str(value).strip()
        value = value.replace(',', '')  # Quitar comas de miles
        value = value.replace('$', '')  # Quitar símbolo de moneda si existe
        value = value.replace(' ', '')  # Quitar espacios
        
        try:
            return Decimal(value)
        except InvalidOperation:
            raise ValidationError('Ingrese un monto válido.')

    def prepare_value(self, value):
        """Prepara el valor para mostrar en el formulario."""
        if value is None or value == '':
            return ''
        try:
            decimal_value = Decimal(str(value))
            # Formato con comas como separador de miles y punto decimal
            return f"{decimal_value:,.2f}".replace(',', 'X').replace('.', '.').replace('X', ',')
        except (InvalidOperation, ValueError):
            return str(value)







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
    # Campo de moneda con formato
    saldo_inicial = MonedaField(
        label="Saldo inicial",
        required=False,
        help_text="Saldo inicial de la cuenta."
    )

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
        }

    def clean_saldo_inicial(self):
        """Si no se proporciona saldo inicial, usar 0."""
        valor = self.cleaned_data.get("saldo_inicial")
        if valor is None:
            return Decimal("0")
        return valor


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
    # Campo de moneda con formato
    monto = MonedaField(
        label="Monto",
        help_text="Monto del movimiento."
    )

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
    # Campo de moneda con formato
    monto = MonedaField(
        label="Monto",
        help_text="Monto del ingreso."
    )

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
    # Campo de moneda con formato
    monto = MonedaField(
        label="Monto",
        help_text="Monto del egreso."
    )

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
    
    monto = MonedaField(
        label="Monto",
        min_value=Decimal('0.01'),
        help_text="Monto a transferir"
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
    
# ==========================================================
# CUENTAS POR PAGAR (CxP) – FORMS
# ==========================================================
class ProveedorFinancieroForm(forms.ModelForm):
    class Meta:
        model = ProveedorFinanciero
        fields = [
            "tipo",
            "tipo_proveedor",
            "nombre",
            "miembro",
            "tipo_documento",
            "documento",
            "telefono",
            "email",
            "direccion",
            "plazo_dias_pago",
            "metodo_pago_preferido",
            "banco",
            "tipo_cuenta",
            "numero_cuenta",
            "titular_cuenta",
            "bloqueado",
            "notas",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Nombre del proveedor o beneficiario"}),
            "documento": forms.TextInput(attrs={"placeholder": "RNC o Cédula (sin guiones)"}),
            "telefono": forms.TextInput(attrs={"placeholder": "Teléfono (opcional)"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email (opcional)"}),
            "direccion": forms.TextInput(attrs={"placeholder": "Dirección (opcional)"}),
            "plazo_dias_pago": forms.NumberInput(attrs={"min": 0, "max": 365}),
            "banco": forms.TextInput(attrs={"placeholder": "Banco (opcional)"}),
            "numero_cuenta": forms.TextInput(attrs={"placeholder": "Número de cuenta (opcional)"}),
            "titular_cuenta": forms.TextInput(attrs={"placeholder": "Titular (opcional)"}),
            "notas": forms.Textarea(attrs={"rows": 2, "placeholder": "Notas (opcional)"}),
        }

    def clean_documento(self):
        cleaned = getattr(self, "cleaned_data", {})

        tipo = (cleaned.get("tipo") or "").strip()          # persona / empresa
        tipo_doc = (cleaned.get("tipo_documento") or "").strip()
        doc = (cleaned.get("documento") or "").strip()

        # Normalizar: quitar espacios y guiones
        doc_norm = re.sub(r"[\s\-]+", "", doc) if doc else ""

        # Si no hay documento, lo dejamos en None (permitido por tu modelo)
        if not doc_norm:
            return None

        # ✅ Inferir tipo_documento según tipo si no viene
        if not tipo_doc:
            if tipo == "persona":
                tipo_doc = "cedula"
            elif tipo == "empresa":
                tipo_doc = "rnc"

            # Guardamos la inferencia en cleaned_data para coherencia del formulario
            self.cleaned_data["tipo_documento"] = tipo_doc

        # ✅ Validaciones estrictas para persona/empresa
        if tipo_doc in ("cedula", "rnc"):
            if not doc_norm.isdigit():
                raise ValidationError("El documento debe contener solo números (sin letras).")

            if tipo_doc == "cedula" and len(doc_norm) != 11:
                raise ValidationError("La cédula debe tener 11 dígitos.")

            if tipo_doc == "rnc" and len(doc_norm) != 9:
                raise ValidationError("El RNC debe tener 9 dígitos.")

        # Pasaporte / otro: se permite texto (pero tú realmente lo quieres forzar a cédula/rnc)
        return doc_norm


    def clean(self):
        cleaned = super().clean()

        metodo = cleaned.get("metodo_pago_preferido") or ""
        banco = (cleaned.get("banco") or "").strip()
        numero = (cleaned.get("numero_cuenta") or "").strip()
        tipo_cuenta = cleaned.get("tipo_cuenta") or ""

        # Si el método preferido es transferencia, pedir banco + cuenta (mínimo)
        if metodo == "transferencia":
            if not banco:
                self.add_error("banco", "Si el método preferido es transferencia, indica el banco.")
            if not numero:
                self.add_error("numero_cuenta", "Si el método preferido es transferencia, indica el número de cuenta.")

        # Si llenó banco o cuenta, que haya coherencia
        if banco and not numero:
            self.add_error("numero_cuenta", "Si indicas banco, completa también el número de cuenta.")
        if numero and not banco:
            self.add_error("banco", "Si indicas número de cuenta, completa también el banco.")

        # Si puso tipo de cuenta, debe tener banco y número
        if tipo_cuenta and (not banco or not numero):
            self.add_error("tipo_cuenta", "Para definir tipo de cuenta, completa banco y número de cuenta.")

        tipo = cleaned.get("tipo") or ""
        if tipo == "persona":
            cleaned["tipo_documento"] = "cedula"
        elif tipo == "empresa":
            cleaned["tipo_documento"] = "rnc"

        return cleaned


class CuentaPorPagarForm(forms.ModelForm):
    # Campo de moneda con formato
    monto_total = MonedaField(
        label="Monto total",
        help_text="Monto total de la cuenta por pagar."
    )

    class Meta:
        model = CuentaPorPagar
     
        fields = [
            "proveedor",
            "fecha_emision",
            "fecha_vencimiento",
            "categoria",
            "cuenta_sugerida",
            "referencia",
            "descripcion",
            "monto_total",
        ]


        widgets = {
            "fecha_emision": forms.DateInput(attrs={"type": "date"}),
            "fecha_vencimiento": forms.DateInput(attrs={"type": "date"}),
            "concepto": forms.TextInput(attrs={"placeholder": "Ej: Pago de sonido, renta local, electricidad..."}),
            "descripcion": forms.Textarea(attrs={"rows": 2, "placeholder": "Detalle (opcional)"}),
            "referencia": forms.TextInput(attrs={"placeholder": "Factura / recibo / contrato (opcional)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Fechas por defecto: hoy (solo cuando el formulario NO está ligado a POST y NO es edición)
        if not self.is_bound and not self.instance.pk:
            hoy = timezone.localdate()
            self.fields["fecha_emision"].initial = hoy
            self.fields["fecha_vencimiento"].initial = hoy

        # Referencia requerida
        self.fields["referencia"].required = True
        self.fields["referencia"].label = "Referencia"
        self.fields["referencia"].help_text = "Número de la cuenta por pagar."

        # Valor por defecto CP001, CP002...
        if not self.is_bound and not self.instance.pk:
            ultimo = (
                CuentaPorPagar.objects
                .filter(referencia__startswith="CP")
                .aggregate(max_ref=Max("referencia"))
                .get("max_ref")
            )

            if ultimo:
                try:
                    numero = int(ultimo.replace("CP", "")) + 1
                except ValueError:
                    numero = 1
            else:
                numero = 1

            self.fields["referencia"].initial = f"CP{numero:03d}"

        # Solo categorías de egreso activas
        self.fields["categoria"].queryset = CategoriaMovimiento.objects.filter(
            tipo="egreso",
            activo=True
        ).order_by("nombre")

        # Solo cuentas activas (para sugerida)
        self.fields["cuenta_sugerida"].queryset = CuentaFinanciera.objects.filter(
            esta_activa=True
        ).order_by("nombre")

        # Proveedores activos
        self.fields["proveedor"].queryset = ProveedorFinanciero.objects.filter(
            activo=True
        ).order_by("nombre")

                # Etiquetas claras (esto es B: sugerido, no contable aún)
        self.fields["categoria"].label = "Categoría (sugerida)"
        self.fields["categoria"].help_text = (
            "No registra el gasto todavía. Sirve para clasificar la CxP y sugerir la categoría al pagar."
        )

        self.fields["cuenta_sugerida"].label = "Cuenta sugerida (opcional)"
        self.fields["cuenta_sugerida"].help_text = "No mueve caja. Solo sugiere desde qué cuenta se pagará normalmente."