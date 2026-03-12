from django import forms
from .models import Visita


class VisitaForm(forms.ModelForm):
    class Meta:
        model = Visita
        fields = [
            "nombre",
            "telefono",
            "tipo",
            "primera_vez",
            "invitado_por",
            "desea_contacto",
            "peticion_oracion",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre completo"
            }),
            "telefono": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "1XXXXXXXXXX",
                "inputmode": "numeric",
                "maxlength": "11",
                "oninput": """
                    let v = this.value.replace(/\\D/g, '');
                    if (v.length > 0 && !v.startsWith('1')) {
                        v = '1' + v;
                    }
                    v = v.slice(0, 11);
                    this.value = v;
                """
            }),
            "tipo": forms.Select(attrs={
                "class": "form-select"
            }),
            "primera_vez": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
            "invitado_por": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "¿Quién le invitó?"
            }),
            "desea_contacto": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
            "peticion_oracion": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Petición de oración (opcional)"
            }),
        }

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono")

        if not telefono:
            return ""

        solo_digitos = "".join(filter(str.isdigit, telefono))

        if len(solo_digitos) == 10:
            solo_digitos = "1" + solo_digitos
        elif len(solo_digitos) == 11 and solo_digitos.startswith("1"):
            pass
        else:
            raise forms.ValidationError(
                "El teléfono debe tener 10 dígitos de RD o 11 incluyendo el 1 al inicio."
            )

        return solo_digitos