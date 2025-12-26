from django import forms

from .models import Unidad, RolUnidad
from django import forms
from django.http import HttpResponse
from .models import Unidad, RolUnidad

from django import forms
from .models import ActividadUnidad, Unidad, UnidadMembresia
from .models import ReporteUnidadPeriodo


from .models import ReporteUnidadCierre

class ReporteCierreForm(forms.ModelForm):
    class Meta:
        model = ReporteUnidadCierre
        fields = ("reflexion", "necesidades", "plan_proximo")

class UnidadForm(forms.ModelForm):
    class Meta:
        model = Unidad
        fields = [
            "nombre",
            "categoria",
            
            "tipo",
            "padre",
            "descripcion",
            "codigo",
            "orden",
            "notas",
            "imagen",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "odoo-name-input",
                "placeholder": "Nombre de la unidad",
                "autocomplete": "off",
            }),
            "categoria": forms.Select(attrs={"class": "odoo-input"}),
            
            "tipo": forms.Select(attrs={"class": "odoo-input"}),
            "padre": forms.Select(attrs={"class": "odoo-input"}),
            "descripcion": forms.Textarea(attrs={
                "class": "odoo-textarea",
                "rows": 4,
                "placeholder": "Descripción breve de la unidad...",
            }),
            "codigo": forms.TextInput(attrs={"class": "odoo-input", "placeholder": "Ej. JUV-01"}),
            "orden": forms.NumberInput(attrs={"class": "odoo-input", "min": 0}),
            "notas": forms.Textarea(attrs={"class": "odoo-textarea", "rows": 4, "placeholder": "Notas internas..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ Tipo (FK) solo activos
        self.fields["tipo"].queryset = self.fields["tipo"].queryset.filter(activo=True)
        self.fields["tipo"].empty_label = None

        # ✅ Categoría (FK) solo activas
        self.fields["categoria"].queryset = self.fields["categoria"].queryset.filter(activo=True)
        self.fields["categoria"].empty_label = None

        # ✅ Defaults al crear (si existe al menos 1)
        if not self.instance.pk and not self.data.get("tipo"):
            first_tipo = self.fields["tipo"].queryset.order_by("orden", "nombre").first()
            if first_tipo:
                self.fields["tipo"].initial = first_tipo.pk

        if not self.instance.pk and not self.data.get("categoria"):
            first_cat = self.fields["categoria"].queryset.order_by("orden", "nombre").first()
            if first_cat:
                self.fields["categoria"].initial = first_cat.pk

        # Padre opcional
        self.fields["padre"].required = False

class RolUnidadForm(forms.ModelForm):
    class Meta:
        model = RolUnidad
        fields = ["nombre", "tipo", "descripcion", "orden", "activo"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }
from django import forms
from .models import ActividadUnidad, Unidad, UnidadMembresia


class ActividadUnidadForm(forms.ModelForm):
    # ✅ Campos extra (NO van dentro de Meta)
    oyentes = forms.IntegerField(min_value=0, required=False, initial=0)
    nuevos_creyentes = forms.IntegerField(min_value=0, required=False, initial=0)
    alcanzados = forms.IntegerField(min_value=0, required=False, initial=0)
    seguimientos = forms.IntegerField(min_value=0, required=False, initial=0)
    observaciones_impacto = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    class Meta:
        model = ActividadUnidad
        fields = [
            "fecha", "titulo", "tipo", "lugar",
            "responsable", "participantes", "notas",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "participantes": forms.CheckboxSelectMultiple(),
            "notas": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, unidad: Unidad = None, **kwargs):
        super().__init__(*args, **kwargs)

        # Limitar participantes a miembros activos de la unidad
        MiembroModel = ActividadUnidad._meta.get_field("participantes").remote_field.model

        if unidad:
            miembros_ids = (
                UnidadMembresia.objects
                .filter(unidad=unidad, activo=True)
                .values_list("miembo_fk_id", flat=True)
                .values_list("miembo_fk_id", flat=True)

            )
            self.fields["participantes"].queryset = (
                MiembroModel.objects.filter(id__in=miembros_ids).order_by("nombres", "apellidos")
            )
        else:
            self.fields["participantes"].queryset = MiembroModel.objects.none()

        # Cargar iniciales desde JSON (al editar)
        datos = (self.instance.datos or {}) if self.instance and self.instance.pk else {}
        self.fields["oyentes"].initial = int(datos.get("oyentes") or 0)
        self.fields["nuevos_creyentes"].initial = int(datos.get("nuevos_creyentes") or 0)
        self.fields["alcanzados"].initial = int(datos.get("alcanzados") or 0)
        self.fields["seguimientos"].initial = int(datos.get("seguimientos") or 0)
        self.fields["observaciones_impacto"].initial = datos.get("observaciones") or ""

    def save(self, commit=True):
        obj = super().save(commit=False)

        datos = obj.datos or {}
        datos["oyentes"] = int(self.cleaned_data.get("oyentes") or 0)
        datos["nuevos_creyentes"] = int(self.cleaned_data.get("nuevos_creyentes") or 0)
        datos["alcanzados"] = int(self.cleaned_data.get("alcanzados") or 0)
        datos["seguimientos"] = int(self.cleaned_data.get("seguimientos") or 0)
        datos["observaciones"] = (self.cleaned_data.get("observaciones_impacto") or "").strip()
        obj.datos = datos

        if commit:
            obj.save()
            self.save_m2m()

        return obj




class ReportePeriodoForm(forms.ModelForm):
    class Meta:
        model = ReporteUnidadPeriodo
        fields = ["reflexion", "necesidades", "plan_proximo"]
        widgets = {
            "reflexion": forms.Textarea(attrs={"rows": 6}),
            "necesidades": forms.Textarea(attrs={"rows": 4}),
            "plan_proximo": forms.Textarea(attrs={"rows": 4}),
        }
