from django import forms
from .models import ConfiguracionSistema


class ConfiguracionGeneralForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionSistema
        fields = [
            "nombre_iglesia",
            "nombre_corto",
            "denominacion",
            "lema",
            "direccion",
            "logo",
            "logo_oscuro",
            "plantilla_pdf_fondo",
        ]
        widgets = {
            "nombre_iglesia": forms.TextInput(attrs={"class": "form-input"}),
            "nombre_corto": forms.TextInput(attrs={"class": "form-input"}),
            "denominacion": forms.TextInput(attrs={"class": "form-input"}),
            "lema": forms.TextInput(attrs={"class": "form-input"}),
            "direccion": forms.Textarea(attrs={"rows": 3}),
        }


class ConfiguracionContactoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionSistema
        fields = ["email_oficial", "telefono_oficial", "whatsapp_oficial"]
        widgets = {
            "email_oficial": forms.EmailInput(attrs={"class": "form-input"}),
            "telefono_oficial": forms.TextInput(attrs={"class": "form-input"}),
            "whatsapp_oficial": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Ej: 18095551234"}
            ),
        }


class ConfiguracionReportesForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionSistema
        fields = [
            "edad_minima_miembro_oficial",
            "zona_horaria",
            "formato_fecha_corta",
            "formato_fecha_larga",
            "color_primario",
            "color_secundario",
            "modo_impresion",
            "pie_cartas",
        ]
        widgets = {
            "edad_minima_miembro_oficial": forms.NumberInput(attrs={"min": 0}),
            "zona_horaria": forms.TextInput(attrs={"class": "form-input"}),
            "formato_fecha_corta": forms.TextInput(attrs={"class": "form-input"}),
            "formato_fecha_larga": forms.TextInput(attrs={"class": "form-input"}),
            "color_primario": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "#0097A7"}
            ),
            "color_secundario": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "#F59E0B"}
            ),
            "pie_cartas": forms.Textarea(attrs={"rows": 3}),
        }
