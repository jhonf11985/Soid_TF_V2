from django import forms
from miembros_app.models import Miembro,ZonaGeo 



class MiembroPortalUpdateForm(forms.ModelForm):
    """
    Form del portal: SOLO campos editables por el miembro.
    Campos internos NO van (notas, salida, códigos internos, etc.).
    Campos bloqueados (fecha_nacimiento, estado_miembro, activo, etc.) NO se editan aquí.
    """
    zona_geo = forms.ModelChoiceField(
        queryset=ZonaGeo.objects.all(),
        required=False,
        empty_label="— Selecciona tu zona (Sector / Ciudad / Provincia) —",
        label="Zona",
    )
    class Meta:
        model = Miembro
        fields = [
            # Foto
            "foto", 

            # Datos básicos (si quieres permitirlos)
            "nombres",
            "apellidos",
           

            # Contacto
            "telefono",
            "telefono_secundario",
            "whatsapp",
            "email",

            # Dirección
            "direccion",
            "sector",
            "ciudad",
            "provincia",
            "codigo_postal",
            "nacionalidad",
            "lugar_nacimiento",

            # Personales
            "estado_civil",
            "nivel_educativo",
            "profesion",
            "pasaporte",

            # Membresía (si quieres que el miembro pueda completarlo)
            "es_trasladado",
            "iglesia_anterior",
            "fecha_conversion",
            "fecha_bautismo",
            "bautizado_confirmado",
            "categoria_miembro",
            "mentor",
            "lider_celula",

            # Emergencia / salud
            "contacto_emergencia_nombre",
            "contacto_emergencia_telefono",
            "contacto_emergencia_relacion",
            "tipo_sangre",
            "alergias",
            "condiciones_medicas",
            "medicamentos",

            # Trabajo
            "empleador",
            "puesto",
            "telefono_trabajo",
            "direccion_trabajo",

            # Socioeconómico
            "tipo_vivienda",
            "situacion_economica",
            "tiene_vehiculo",
            "vehiculo_tipo",
            "vehiculo_marca",
            "vehiculo_placa",

            # Intereses
            "intereses",
            "habilidades",
            "otros_intereses",
            "otras_habilidades",
        ]

        widgets = {
            "direccion": forms.Textarea(attrs={"rows": 2}),
            "alergias": forms.Textarea(attrs={"rows": 2}),
            "condiciones_medicas": forms.Textarea(attrs={"rows": 2}),
            "medicamentos": forms.Textarea(attrs={"rows": 2}),
            "direccion_trabajo": forms.Textarea(attrs={"rows": 2}),
            "intereses": forms.Textarea(attrs={"rows": 2}),
            "habilidades": forms.Textarea(attrs={"rows": 2}),
            "otros_intereses": forms.Textarea(attrs={"rows": 2}),
            "otras_habilidades": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Clases CSS simples (por si tu template las usa)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "pm-check"})
            else:
                field.widget.attrs.update({"class": "pm-input"})

        # Placeholder útil
        if "telefono" in self.fields:
            self.fields["telefono"].widget.attrs.update({"placeholder": "Ej: 8091234567"})
        if "whatsapp" in self.fields:
            self.fields["whatsapp"].widget.attrs.update({"placeholder": "Ej: 8091234567"})

        # ZonaGeo como select bonito
        self.fields["zona_geo"].queryset = ZonaGeo.objects.all().order_by("provincia", "ciudad", "sector")
        self.fields["zona_geo"].widget.attrs.update({"class": "pm-input"})

        # Initial: si el miembro ya tiene sector/ciudad/provincia, marcamos la ZonaGeo
        if self.instance and getattr(self.instance, "pk", None):
            s = (getattr(self.instance, "sector", "") or "").strip()
            c = (getattr(self.instance, "ciudad", "") or "").strip()
            p = (getattr(self.instance, "provincia", "") or "").strip()
            try:
                self.fields["zona_geo"].initial = ZonaGeo.objects.get(sector=s, ciudad=c, provincia=p)
            except ZonaGeo.DoesNotExist:
                pass
    def save(self, commit=True):
        obj = super().save(commit=False)

        zona = self.cleaned_data.get("zona_geo")
        if zona:
            # Copiamos la zona elegida al perfil del miembro
            obj.sector = (zona.sector or "").strip()
            obj.ciudad = (zona.ciudad or "").strip()
            obj.provincia = (zona.provincia or "").strip()

        if commit:
            obj.save()
            self.save_m2m()

        return obj
