import re
from django import forms
from .models import SolicitudActualizacionMiembro, SolicitudAltaMiembro
from miembros_app.models import GENERO_CHOICES, ESTADO_MIEMBRO_CHOICES, CIUDAD_CHOICES
from datetime import date
from django.utils import timezone


class SolicitudActualizacionForm(forms.ModelForm):
    """
    Formulario público para actualización de datos.
    Permite recortar campos dinámicamente con allowed_fields.
    """

    def __init__(self, *args, **kwargs):
        allowed_fields = kwargs.pop("allowed_fields", None)
        super().__init__(*args, **kwargs)

        if allowed_fields:
            allowed = set(allowed_fields)
            for name in list(self.fields.keys()):
                if name not in allowed:
                    self.fields.pop(name)

        self.allowed_fields = list(self.fields.keys())

    def clean_pasaporte(self):
        pasaporte = (self.cleaned_data.get("pasaporte") or "").strip()
        if not pasaporte:
            return ""

        pasaporte = re.sub(r"[\s-]+", "", pasaporte)
        pasaporte = re.sub(r"[^A-Za-z0-9]", "", pasaporte)
        pasaporte = pasaporte.upper()

        if not (6 <= len(pasaporte) <= 15):
            raise forms.ValidationError(
                "Pasaporte inválido. Usa solo letras y números (6 a 15 caracteres)."
            )
        return pasaporte

    def clean_telefono_secundario(self):
        raw = (self.cleaned_data.get("telefono_secundario") or "").strip()
        if not raw:
            return ""

        digits = "".join(c for c in raw if c.isdigit())

        if len(digits) == 10 and digits.startswith(("809", "829", "849")):
            return "+1" + digits

        if len(digits) == 11 and digits.startswith("1"):
            if digits[1:4] in ("809", "829", "849"):
                return "+" + digits

        raise forms.ValidationError(
            "Teléfono secundario inválido. Ejemplo: 8091234567."
        )

    class Meta:
        model = SolicitudActualizacionMiembro
        fields = [
            "telefono", "whatsapp", "email",
            "direccion", "sector", "ciudad", "provincia", "codigo_postal",
            "empleador", "puesto", "telefono_trabajo", "direccion_trabajo",
            "contacto_emergencia_nombre", "contacto_emergencia_telefono", "contacto_emergencia_relacion",
            "tipo_sangre", "alergias", "condiciones_medicas", "medicamentos",
            "telefono_secundario",
            "lugar_nacimiento",
            "nacionalidad",
            "estado_civil",
            "nivel_educativo",
            "profesion",
            "pasaporte",
        ]
        widgets = {
            "direccion": forms.Textarea(attrs={"rows": 2}),
            "direccion_trabajo": forms.Textarea(attrs={"rows": 2}),
            "alergias": forms.Textarea(attrs={"rows": 2}),
            "condiciones_medicas": forms.Textarea(attrs={"rows": 2}),
            "medicamentos": forms.Textarea(attrs={"rows": 2}),
        }


class SolicitudAltaPublicaForm(forms.ModelForm):
    """Formulario público para alta masiva."""

    # Choices de sectores (igual que en el template original)
    SECTOR_CHOICES = [
        ("", "Selecciona tu sector"),
        ("21 de Enero", "21 de Enero"),
        ("30 de Mayo", "30 de Mayo"),
        ("Ana Melia", "Ana Melia"),
        ("Anamuya", "Anamuya"),
        ("Antonio Guzmán", "Antonio Guzmán"),
        ("Brisas del Duey", "Brisas del Duey"),
        ("Cristo Rey", "Cristo Rey"),
        ("Don Celso", "Don Celso"),
        ("Duarte", "Duarte"),
        ("Juan Pablo Duarte", "Juan Pablo Duarte"),
        ("El Bonao", "El Bonao"),
        ("El Centro", "El Centro"),
        ("El Chorro", "El Chorro"),
        ("El Macao", "El Macao"),
        ("El Obispado", "El Obispado"),
        ("El Tamarindo", "El Tamarindo"),
        ("La Altagracia", "La Altagracia"),
        ("La Aviación", "La Aviación"),
        ("La Cabrera", "La Cabrera"),
        ("La Candelaria", "La Candelaria"),
        ("La Ceiba del Salado", "La Ceiba del Salado"),
        ("La Colonia", "La Colonia"),
        ("La Cruz", "La Cruz"),
        ("La Fe", "La Fe"),
        ("La Laguna", "La Laguna"),
        ("La Malena", "La Malena"),
        ("La Mina", "La Mina"),
        ("La Otra Banda", "La Otra Banda"),
        ("Las Caobas", "Las Caobas"),
        ("Las Flores", "Las Flores"),
        ("Las Mercedes", "Las Mercedes"),
        ("Los Platanitos", "Los Platanitos"),
        ("Los Ríos", "Los Ríos"),
        ("Los Sotos", "Los Sotos"),
        ("Luisa Perla", "Luisa Perla"),
        ("Mamá Tingó", "Mamá Tingó"),
        ("Nazaret", "Nazaret"),
        ("San Francisco", "San Francisco"),
        ("San José", "San José"),
        ("San Martín", "San Martín"),
        ("San Pedro", "San Pedro"),
        ("Santa Cruz", "Santa Cruz"),
        ("Santana", "Santana"),
        ("Savica", "Savica"),
        ("Villa Cerro", "Villa Cerro"),
        ("Villa Hortensia", "Villa Hortensia"),
        ("Villa María", "Villa María"),
        ("Villa Palmera", "Villa Palmera"),
        ("Villa Progreso", "Villa Progreso"),
        ("Yuma", "Yuma"),
        ("Otro", "Otro / No aparece en la lista"),
    ]

    sector = forms.ChoiceField(
        choices=SECTOR_CHOICES,
        widget=forms.Select(attrs={"class": "odoo-input odoo-select"}),
        error_messages={"required": "Debes seleccionar un sector."}
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer ciudad requerido con mensaje personalizado
        self.fields["ciudad"].error_messages = {"required": "Debes seleccionar una ciudad."}

    def _normalizar_rd_a_e164(self, raw: str, requerido: bool, campo: str) -> str:
        raw = (raw or "").strip()
        if not raw:
            if requerido:
                raise forms.ValidationError(f"El campo {campo} es obligatorio.")
            return ""

        digits = "".join(c for c in raw if c.isdigit())

        if len(digits) == 10 and digits.startswith(("809", "829", "849")):
            return "+1" + digits

        if len(digits) == 11 and digits.startswith("1"):
            if digits[1:4] in ("809", "829", "849"):
                return "+" + digits

        if raw.startswith("+") and len(digits) == 11 and digits.startswith("1"):
            if digits[1:4] in ("809", "829", "849"):
                return "+" + digits

        raise forms.ValidationError(
            f"{campo} inválido para RD. Ejemplo: 8091234567."
        )

    def clean_nombres(self):
        return (self.cleaned_data.get("nombres") or "").strip()

    def clean_apellidos(self):
        return (self.cleaned_data.get("apellidos") or "").strip()

    def clean_telefono(self):
        return self._normalizar_rd_a_e164(
            self.cleaned_data.get("telefono"),
            requerido=False,  # Ya no obligatorio
            campo="Teléfono",
        )

    def clean_whatsapp(self):
        return self._normalizar_rd_a_e164(
            self.cleaned_data.get("whatsapp"),
            requerido=False,
            campo="WhatsApp",
        )


    def clean(self):
        cleaned = super().clean()

        fn = cleaned.get("fecha_nacimiento")
        fi = cleaned.get("fecha_ingreso_iglesia")

        hoy = timezone.localdate()

        # Rangos razonables (ajústalos si quieres)
        min_nacimiento = date(1900, 1, 1)
        max_nacimiento = hoy  # no nacimientos futuros

        min_ingreso = date(1900, 1, 1)
        max_ingreso = hoy  # no ingresos futuros (si quieres permitir futuro, te lo cambio)

        # Validar nacimiento
        if fn:
            if fn < min_nacimiento or fn > max_nacimiento:
                self.add_error(
                    "fecha_nacimiento",
                    "Fecha de nacimiento inválida. Debe estar entre 1900 y hoy."
                )

        # Validar ingreso
        if fi:
            if fi < min_ingreso or fi > max_ingreso:
                self.add_error(
                    "fecha_ingreso_iglesia",
                    "Fecha de ingreso inválida. Debe estar entre 1900 y hoy."
                )

        # Regla lógica: nacimiento no puede ser mayor que ingreso
        if fn and fi and fn > fi:
            self.add_error(
                "fecha_nacimiento",
                "La fecha de nacimiento no puede ser mayor que la fecha de ingreso a la iglesia."
            )

        # Extra recomendado: edad máxima (ej. 120 años)
        if fn:
            edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
            if edad > 120:
                self.add_error("fecha_nacimiento", "Fecha de nacimiento inválida (edad no razonable).")

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.estado_miembro = "activo"
        if commit:
            instance.save()
        return instance

    class Meta:
        model = SolicitudAltaMiembro
        fields = [
            "nombres",
            "apellidos",
            "genero",
            "fecha_nacimiento",
            "fecha_ingreso_iglesia",
            "telefono",
            "whatsapp",
            "direccion",
            "sector",
            "ciudad",
            "cedula",
            "foto",
        ]
        widgets = {
            "nombres": forms.TextInput(attrs={
                "class": "odoo-input",
                "placeholder": "Nombres"
            }),
            "apellidos": forms.TextInput(attrs={
                "class": "odoo-input",
                "placeholder": "Apellidos"
            }),
            "genero": forms.Select(attrs={
                "class": "odoo-input odoo-select"
            }),


  
            "fecha_nacimiento": forms.DateInput(attrs={
                "class": "odoo-input",
                "type": "date",
                "min": "1900-01-01",
                "max": timezone.localdate().isoformat(),
            }),
            "fecha_ingreso_iglesia": forms.DateInput(attrs={
                "class": "odoo-input",
                "type": "date",
                "min": "1900-01-01",
                "max": timezone.localdate().isoformat(),
            }),
  
            "telefono": forms.TextInput(attrs={
                "class": "odoo-input",
                "placeholder": "809-123-4567 (opcional)",
                "inputmode": "numeric",
                "autocomplete": "tel",
            }),
            "whatsapp": forms.TextInput(attrs={
                "class": "odoo-input",
                "placeholder": "+18091234567",
                "readonly": "readonly",
                "tabindex": "-1",
            }),
            "cedula": forms.TextInput(attrs={
                "class": "odoo-input",
                "placeholder": "Cédula (opcional)",
                "inputmode": "numeric",
            }),
            "foto": forms.ClearableFileInput(attrs={
                "class": "odoo-input",
                "accept": "image/*",
            }),
            "direccion": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": "Dirección (opcional)"
            }),
            "sector": forms.Select(attrs={
                "class": "odoo-input odoo-select",
            }),
            "ciudad": forms.Select(attrs={
                "class": "odoo-input odoo-select",
            }),
        }


class ActualizacionDatosConfigForm(forms.Form):
    """Form para configurar qué campos se muestran en el formulario público."""
    
    activo = forms.BooleanField(
        required=False,
        initial=True,
        label="Formulario público activo"
    )

    campos_permitidos = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[],
        label="Campos a solicitar (público)"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["campos_permitidos"].choices = [
            ("telefono", "Teléfono"),
            ("whatsapp", "WhatsApp"),
            ("email", "Email"),
            ("direccion", "Dirección"),
            ("sector", "Sector"),
            ("ciudad", "Ciudad"),
            ("provincia", "Provincia"),
            ("codigo_postal", "Código postal"),
            ("empleador", "Empleador"),
            ("puesto", "Puesto"),
            ("telefono_trabajo", "Teléfono trabajo"),
            ("direccion_trabajo", "Dirección trabajo"),
            ("contacto_emergencia_nombre", "Contacto emergencia (Nombre)"),
            ("contacto_emergencia_telefono", "Contacto emergencia (Teléfono)"),
            ("contacto_emergencia_relacion", "Contacto emergencia (Relación)"),
            ("tipo_sangre", "Tipo de sangre"),
            ("alergias", "Alergias"),
            ("condiciones_medicas", "Condiciones médicas"),
            ("medicamentos", "Medicamentos"),
            ("telefono_secundario", "Teléfono secundario"),
            ("lugar_nacimiento", "Lugar de nacimiento"),
            ("nacionalidad", "Nacionalidad"),
            ("estado_civil", "Estado civil"),
            ("nivel_educativo", "Nivel educativo"),
            ("profesion", "Profesión"),
            ("pasaporte", "Pasaporte"),
        ]