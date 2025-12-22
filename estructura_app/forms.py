from django import forms

from .models import Unidad, RolUnidad
from django import forms
from django.http import HttpResponse
from .models import Unidad, RolUnidad

from django import forms
from .models import ActividadUnidad, Unidad, UnidadMembresia
from .models import ReporteUnidadPeriodo




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
class ActividadUnidadForm(forms.ModelForm):
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

        MiembroModel = ActividadUnidad._meta.get_field(
            "participantes"
        ).remote_field.model

        if unidad:
            miembros_ids = (
                UnidadMembresia.objects
                .filter(unidad=unidad, activo=True)
                .values_list("miembo_fk_id", flat=True)
            )

            self.fields["participantes"].queryset = (
                MiembroModel.objects
                .filter(id__in=miembros_ids)
                .order_by("nombres", "apellidos")
            )
        else:
            self.fields["participantes"].queryset = MiembroModel.objects.none()



    def save(self, commit=True):
        obj = super().save(commit=False)

        # Guardar métricas específicas de evangelismo dentro de datos


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
