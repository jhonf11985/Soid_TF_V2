from django import forms
from .models import ConfiguracionSistema
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group



import re

def _formatear_cedula(valor):
    if not valor:
        return ""

    numeros = re.sub(r"\D", "", valor)[:9]

    if len(numeros) <= 3:
        return numeros
    if len(numeros) <= 7:
        return f"{numeros[:3]}-{numeros[3:]}"
    return f"{numeros[:3]}-{numeros[3:7]}-{numeros[7:]}"


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
            
            "codigo_iglesia",
            "presbiterio_nombre",
            "presbitero_nombre",
            "conyuge_pastor",
            "credencial_pastor",
            "credencial_conyuge",

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
    def clean_credencial_pastor(self):
        return _formatear_cedula(self.cleaned_data.get("credencial_pastor"))

    def clean_credencial_conyuge(self):
        return _formatear_cedula(self.cleaned_data.get("credencial_conyuge"))


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
        required=True,
        widget=forms.Select(attrs={
            "class": "form-input",
        })
    )

    # ya lo tienes
    miembro_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )

    # ✅ NUEVO: si el admin decide editar manualmente nombre/apellidos
    override_nombre = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput()
    )

    def clean_miembro_id(self):
        """
        Limpia el campo miembro_id:
        - Convierte string vacío a None
        - Valida que el miembro exista y no esté ya vinculado
        """
        miembro_id = self.cleaned_data.get("miembro_id")
        
        # Si viene vacío (string vacío o None), retornar None
        if not miembro_id:
            return None
        
        # Asegurar que sea entero
        try:
            miembro_id = int(miembro_id)
        except (ValueError, TypeError):
            return None
        
        from miembros_app.models import Miembro
        miembro = Miembro.objects.filter(id=miembro_id).first()
        
        if not miembro:
            raise forms.ValidationError("El miembro seleccionado no existe.")
        
        # Verificar que no esté ya vinculado a otro usuario
        if miembro.usuario is not None:
            raise forms.ValidationError(
                f"Este miembro ya está vinculado al usuario «{miembro.usuario.username}»."
            )
        
        return miembro_id

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            return email

        qs = User.objects.filter(email__iexact=email)

        # ✅ si estoy editando, excluir mi propio usuario
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                "Ya existe otro usuario con este correo electrónico."
            )

        return email

    def _get_miembro_nombres(self, miembro):
        """
        Intentamos encontrar nombre/apellidos con varios nombres de campos posibles,
        para no romper si tu modelo Miembro usa otro naming.
        """
        # Ajusta este orden si tú sabes exactamente cómo se llaman.
        nombre = (
            getattr(miembro, "nombre", None)
            or getattr(miembro, "nombres", None)
            or getattr(miembro, "first_name", None)
            or getattr(miembro, "primer_nombre", None)
            or ""
        )
        apellidos = (
            getattr(miembro, "apellido", None)
            or getattr(miembro, "apellidos", None)
            or getattr(miembro, "last_name", None)
            or getattr(miembro, "segundo_nombre", None)  # (por si lo usas así)
            or ""
        )
        return (str(nombre).strip(), str(apellidos).strip())

    def save(self, commit=True):
        user = super().save(commit=False)

        # Datos normales del form
        miembro_id = self.cleaned_data.get("miembro_id")

        if miembro_id:
            from miembros_app.models import Miembro
            miembro = Miembro.objects.filter(id=miembro_id).first()
            if miembro and miembro.email:
                user.email = miembro.email  # 🔥 el miembro manda
            else:
                user.email = self.cleaned_data.get("email", "")
        else:
            user.email = self.cleaned_data.get("email", "")


        miembro_id = self.cleaned_data.get("miembro_id")
        override = bool(self.cleaned_data.get("override_nombre"))

        # ✅ Regla híbrida:
        # Si se vinculó miembro y NO se activó edición manual,
        # el nombre/apellido del usuario se toma del Miembro (fuente de verdad).
        if miembro_id and not override:
            from miembros_app.models import Miembro  # import local para evitar líos
            miembro = Miembro.objects.filter(id=miembro_id).first()
            if miembro:
                nombre, apellidos = self._get_miembro_nombres(miembro)
                # si por alguna razón vienen vacíos, cae al form
                user.first_name = nombre or self.cleaned_data.get("first_name", "")
                user.last_name = apellidos or self.cleaned_data.get("last_name", "")
            else:
                user.first_name = self.cleaned_data.get("first_name", "")
                user.last_name = self.cleaned_data.get("last_name", "")
        else:
            # Edición manual o sin miembro
            user.first_name = self.cleaned_data.get("first_name", "")
            user.last_name = self.cleaned_data.get("last_name", "")

        if commit:
            user.save()
            grupo = self.cleaned_data.get("grupo")
            if grupo:
                user.groups.set([grupo])

        return user

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
            "miembro_id",
            "override_nombre",
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

class UsuarioIglesiaEditForm(forms.ModelForm):
    grupo = forms.ModelChoiceField(
        label="Rol / Grupo",
        queryset=Group.objects.all(),
        required=True,
        widget=forms.Select(attrs={"class": "form-input"})
    )

    miembro_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    override_nombre = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Precargar el grupo actual del usuario
        if self.instance and self.instance.pk:
            grupo_actual = self.instance.groups.first()
            if grupo_actual:
                self.fields['grupo'].initial = grupo_actual

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            return email

        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        usuario_existente = qs.first()
        if usuario_existente:
            raise forms.ValidationError(
                f"Ya existe otro usuario con este correo: «{usuario_existente.username}»."
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        miembro_id = self.cleaned_data.get("miembro_id")
        override = bool(self.cleaned_data.get("override_nombre"))

        if miembro_id and not override:
            from miembros_app.models import Miembro
            miembro = Miembro.objects.filter(id=miembro_id).first()
            if miembro:
                user.first_name = getattr(miembro, "nombre", "") or self.cleaned_data.get("first_name", "")
                user.last_name = getattr(miembro, "apellido", "") or self.cleaned_data.get("last_name", "")

        if commit:
            user.save()
            grupo = self.cleaned_data.get("grupo")
            if grupo:
                user.groups.set([grupo])

        return user

    def clean_miembro_id(self):
        miembro_id = self.cleaned_data.get("miembro_id")
        
        # Si viene vacío, retornar None
        if not miembro_id:
            return None
        
        # Asegurar que sea entero
        try:
            miembro_id = int(miembro_id)
        except (ValueError, TypeError):
            return None

        from miembros_app.models import Miembro
        miembro = Miembro.objects.filter(id=miembro_id).first()

        if not miembro:
            raise forms.ValidationError("El miembro seleccionado no existe.")

        # Verificar que no esté ya vinculado a OTRO usuario
        if miembro.usuario is not None:
            # Si el miembro ya está vinculado al usuario actual, está OK
            if self.instance and self.instance.pk and miembro.usuario.pk == self.instance.pk:
                return miembro_id
            # Si está vinculado a otro usuario, error
            raise forms.ValidationError(
                f"⚠️ Este miembro ya está vinculado al usuario «{miembro.usuario.username}»."
            )

        return miembro_id

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-input"}),
            "first_name": forms.TextInput(attrs={"class": "form-input"}),
            "last_name": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
        }