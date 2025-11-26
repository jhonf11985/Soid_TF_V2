from django import forms
from .models import ConfiguracionSistema


class ConfiguracionGeneralForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionSistema
        fields = ["nombre_iglesia", "direccion", "logo"]
        widgets = {
            "nombre_iglesia": forms.TextInput(attrs={"class": "form-input"}),
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
        fields = ["edad_minima_miembro_oficial", "pie_cartas"]
        widgets = {
            "edad_minima_miembro_oficial": forms.NumberInput(attrs={"min": 0}),
            "pie_cartas": forms.Textarea(attrs={"rows": 3}),
        }
