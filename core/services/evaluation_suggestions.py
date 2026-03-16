# core/services/evaluation_suggestions.py
from django.utils import timezone

from evaluaciones_app.models import EvaluacionUnidad
from estructura_app.models import UnidadCargo, Unidad


class EvaluationSuggestionService:
    """
    Devuelve una sugerencia simple de evaluación para el usuario.
    """

    @classmethod
    def get_suggestion_for_user(cls, user):
        if not hasattr(user, "miembro") or not user.miembro:
            return None

        miembro = user.miembro  # También corregí el nombre de variable
        hoy = timezone.now()

        # 1) Unidades donde el miembro es liderazgo
        unidades_ids = (
            UnidadCargo.objects.filter(
                miembo_fk=miembro,  # ✅ CORREGIDO
                rol__tipo="LIDERAZGO",
            )
            .values_list("unidad_id", flat=True)
            .distinct()
        )

        # 2) Recorremos unidades y buscamos si falta evaluación del mes
        unidades = Unidad.objects.filter(id__in=unidades_ids)

        for unidad in unidades:
            evaluacion = EvaluacionUnidad.objects.filter(
                unidad=unidad,
                anio=hoy.year,
                mes=hoy.month,
            ).first()

            if not evaluacion:
                return {
                    "unidad_id": unidad.id,
                    "unidad_nombre": getattr(unidad, "nombre", str(unidad)),
                    "tipo": "iniciar",
                }

        return None