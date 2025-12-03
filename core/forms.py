from django import forms
from .models import ConfiguracionSistema
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group



class ConfiguracionGeneralForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionSistema
        fields = [
            "nombre_iglesia",
            "nombre_corto",
            "denominacion",
            "lema",
            "direccion",
            "pastor_principal",
            "email_pastor",
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
            "pastor_principal": forms.TextInput(attrs={"class": "form-input"}),
            "email_pastor": forms.EmailInput(attrs={"class": "form-input"}),
        }

class ConfiguracionContactoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionSistema
        fields = [
            "email_oficial",
            "telefono_oficial",
            "whatsapp_oficial",
            "encargado_comunicaciones",
            "horario_atencion",
            "sitio_web",
            "facebook_url",
            "instagram_url",
            "mensaje_institucional_corto",
        ]
        widgets = {
            "email_oficial": forms.EmailInput(attrs={
                "class": "form-input",
                "placeholder": "Ej: correo@dominio.com"
            }),
            "telefono_oficial": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Ej: 8095551234"
            }),
            "whatsapp_oficial": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Ej: 18095551234"
            }),

            "encargado_comunicaciones": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Ej: Secretaría, Administración"
            }),
            "horario_atencion": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Ej: Lun–Vie 9:00 a.m. – 6:00 p.m."
            }),

            "sitio_web": forms.URLInput(attrs={
                "class": "form-input",
                "placeholder": "Ej: https://www.ejemplo.com"
            }),
            "facebook_url": forms.URLInput(attrs={
                "class": "form-input",
                "placeholder": "Ej: https://facebook.com/usuario"
            }),
            "instagram_url": forms.URLInput(attrs={
                "class": "form-input",
                "placeholder": "Ej: https://instagram.com/usuario"
            }),

            "mensaje_institucional_corto": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Ej: Un mensaje breve y significativo"
            }),
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
            "mostrar_logo_en_reportes",
            "mostrar_direccion_en_reportes",
            "email_from_name",
            "email_from_address",
            "enviar_copia_a_pastor",
            "codigo_miembro_prefijo",   # 👈 AÑADIDO AQUÍ
            
        ]
        widgets = {
            "edad_minima_miembro_oficial": forms.NumberInput(attrs={"min": 0}),
            "zona_horaria": forms.TextInput(attrs={"class": "form-input"}),
            "formato_fecha_corta": forms.TextInput(attrs={"class": "form-input"}),
            "formato_fecha_larga": forms.TextInput(attrs={"class": "form-input"}),

            # 🎨 PICKER DE COLOR
            "color_primario": forms.TextInput(
                attrs={
                    "type": "color",
                    "class": "form-input",
                    "style": "padding:0; width:70px; height:32px; cursor:pointer;",
                }
            ),
            "color_secundario": forms.TextInput(
                attrs={
                    "type": "color",
                    "class": "form-input",
                    "style": "padding:0; width:70px; height:32px; cursor:pointer;",
                }
            ),

            "pie_cartas": forms.Textarea(attrs={"rows": 3}),
            "email_from_name": forms.TextInput(attrs={"class": "form-input"}),
            "email_from_address": forms.EmailInput(attrs={"class": "form-input"}),
        }
class UsuarioIglesiaForm(UserCreationForm):
    first_name = forms.CharField(
        label="Nombre",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Ej.: María"
        })
    )
    last_name = forms.CharField(
        label="Apellidos",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Ej.: Martínez Pérez"
        })
    )
    email = forms.EmailField(
        label="Correo electrónico",
        required=True,
        widget=forms.EmailInput(attrs={
            "class": "form-input",
            "placeholder": "ejemplo@correo.com"
        })
    )
    grupo = forms.ModelChoiceField(
        label="Rol / Grupo",
        queryset=Group.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            "class": "form-input",
        })
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "grupo",
            "password1",
            "password2",
        ]
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Nombre de usuario"
            }),
            "password1": forms.PasswordInput(attrs={
                "class": "form-input",
                "placeholder": "Contraseña segura"
            }),
            "password2": forms.PasswordInput(attrs={
                "class": "form-input",
                "placeholder": "Confirmar contraseña"
            }),
        }
