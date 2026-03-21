from django import forms
from .models import (
    Unidad, RolUnidad, TipoUnidad, CategoriaUnidad,
    ActividadUnidad, UnidadMembresia, MovimientoUnidad,
    ReporteUnidadPeriodo, ReporteUnidadCierre
)


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
            "hereda_liderazgo",
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
            "hereda_liderazgo": forms.CheckboxInput(attrs={"class": "odoo-checkbox"}),
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

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

        if tenant:
            self.fields["tipo"].queryset = TipoUnidad.objects.filter(tenant=tenant, activo=True)
            self.fields["categoria"].queryset = CategoriaUnidad.objects.filter(tenant=tenant, activo=True)
            self.fields["padre"].queryset = Unidad.objects.filter(tenant=tenant, activa=True)
        else:
            self.fields["tipo"].queryset = self.fields["tipo"].queryset.filter(activo=True)
            self.fields["categoria"].queryset = self.fields["categoria"].queryset.filter(activo=True)

        self.fields["tipo"].empty_label = None
        self.fields["categoria"].empty_label = None

        if not self.instance.pk and not self.data.get("tipo"):
            first_tipo = self.fields["tipo"].queryset.order_by("orden", "nombre").first()
            if first_tipo:
                self.fields["tipo"].initial = first_tipo.pk

        if not self.instance.pk and not self.data.get("categoria"):
            first_cat = self.fields["categoria"].queryset.order_by("orden", "nombre").first()
            if first_cat:
                self.fields["categoria"].initial = first_cat.pk

        self.fields["padre"].required = False

    def _parse_edad(self, field_name):
        """
        Parsea un campo de edad desde self.data.
        Retorna (valor_int, error_msg) donde error_msg es None si es válido.
        """
        raw = (self.data.get(field_name) or "").strip()
        
        if raw == "":
            return None, None
        
        try:
            valor = int(raw)
            return valor, None
        except ValueError:
            return None, f"El campo '{field_name}' debe ser un número válido."

    def clean(self):
        cleaned_data = super().clean()
        errors = []

        # ═══════════════════════════════════════════════════════════════════
        # PARSEAR VALORES DE EDAD
        # ═══════════════════════════════════════════════════════════════════
        edad_min, err_min = self._parse_edad("edad_min")
        edad_max, err_max = self._parse_edad("edad_max")

        if err_min:
            errors.append(err_min)
        if err_max:
            errors.append(err_max)

        # Si hay errores de parseo, no continuar con validaciones
        if errors:
            raise forms.ValidationError(errors)

        # ═══════════════════════════════════════════════════════════════════
        # VALIDAR: EDADES NO NEGATIVAS
        # ═══════════════════════════════════════════════════════════════════
        if edad_min is not None and edad_min < 0:
            errors.append("La edad mínima no puede ser negativa.")

        if edad_max is not None and edad_max < 0:
            errors.append("La edad máxima no puede ser negativa.")

        # ═══════════════════════════════════════════════════════════════════
        # VALIDAR: RANGO COHERENTE (max >= min)
        # ═══════════════════════════════════════════════════════════════════
        if edad_min is not None and edad_max is not None:
            if edad_max < edad_min:
                errors.append(
                    f"La edad máxima ({edad_max} años) no puede ser menor "
                    f"que la edad mínima ({edad_min} años)."
                )

        # ═══════════════════════════════════════════════════════════════════
        # VALIDAR: SI PERMITE VISITAS, REQUIERE RANGO COMPLETO
        # ═══════════════════════════════════════════════════════════════════
        permite_visitas = self.data.get("regla_perm_visitas") in ["on", "true", "1", "True"]

        if permite_visitas:
            if edad_min is None and edad_max is None:
                errors.append(
                    "Para permitir visitas debes especificar el rango de edad "
                    "(edad mínima y edad máxima)."
                )
            elif edad_min is None:
                errors.append(
                    "Para permitir visitas debes especificar la edad mínima."
                )
            elif edad_max is None:
                errors.append(
                    "Para permitir visitas debes especificar la edad máxima."
                )

        # ═══════════════════════════════════════════════════════════════════
        # VALIDAR: SI SOLO UNA EDAD ESTÁ PRESENTE (sin visitas), ADVERTIR
        # ═══════════════════════════════════════════════════════════════════
        # Opcional: Si quieres que siempre se requieran ambas cuando hay una
        # Descomenta las siguientes líneas:
        #
        # if (edad_min is not None) != (edad_max is not None):
        #     errors.append(
        #         "Si defines un rango de edad, debes especificar tanto "
        #         "la edad mínima como la edad máxima."
        #     )

        # ═══════════════════════════════════════════════════════════════════
        # LANZAR TODOS LOS ERRORES JUNTOS
        # ═══════════════════════════════════════════════════════════════════
        if errors:
            raise forms.ValidationError(errors)

        return cleaned_data

    def save(self, commit=True):
        obj = super().save(commit=False)
        if not obj.pk and self.tenant:
            obj.tenant = self.tenant
        if commit:
            obj.save()
        return obj


class RolUnidadForm(forms.ModelForm):
    class Meta:
        model = RolUnidad
        fields = ["nombre", "tipo", "descripcion", "orden", "activo"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

    def save(self, commit=True):
        obj = super().save(commit=False)
        if not obj.pk and self.tenant:
            obj.tenant = self.tenant
        if commit:
            obj.save()
        return obj


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

    def __init__(self, *args, unidad: Unidad = None, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.unidad = unidad

        # Limitar participantes a miembros activos de la unidad
        MiembroModel = ActividadUnidad._meta.get_field("participantes").remote_field.model

        if unidad:
            qs_membresias = UnidadMembresia.objects.filter(unidad=unidad, activo=True)
            if tenant:
                qs_membresias = qs_membresias.filter(tenant=tenant)
            
            miembros_ids = qs_membresias.values_list("miembo_fk_id", flat=True)
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

        # Asignar tenant si es nuevo
        if not obj.pk and self.tenant:
            obj.tenant = self.tenant

        # Asignar unidad si se pasó
        if self.unidad and not obj.unidad_id:
            obj.unidad = self.unidad

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

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

    def save(self, commit=True):
        obj = super().save(commit=False)
        if not obj.pk and self.tenant:
            obj.tenant = self.tenant
        if commit:
            obj.save()
        return obj


class MovimientoUnidadForm(forms.ModelForm):
    class Meta:
        model = MovimientoUnidad
        fields = ["tipo", "fecha", "monto", "concepto", "descripcion"]
        widgets = {
            "tipo": forms.Select(),
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "monto": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "concepto": forms.TextInput(attrs={"placeholder": "Ej: Ofrenda, Actividad, Compra, Transporte..."}),
            "descripcion": forms.Textarea(attrs={"rows": 3, "placeholder": "Opcional"}),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

    def save(self, commit=True):
        obj = super().save(commit=False)
        if not obj.pk and self.tenant:
            obj.tenant = self.tenant
        if commit:
            obj.save()
        return obj


class MovimientoUnidadEditarForm(forms.ModelForm):
    class Meta:
        model = MovimientoUnidad
        fields = ["fecha", "concepto"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "concepto": forms.TextInput(attrs={"placeholder": "Ej: Ofrenda, Actividad, Compra, Transporte."}),
        }