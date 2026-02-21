# core/services/evaluation_suggestions.py
from django.utils import timezone

# IMPORTS (ajusta si tus modelos están en otro sitio)
from evaluaciones_app.models import EvaluacionUnidad
from estructura_app.models import UnidadCargo, Unidad


class EvaluationSuggestionService:
    """
    Devuelve una sugerencia simple de evaluación para el usuario.
    (Por ahora: si lidera una unidad y NO existe evaluación del mes, se sugiere iniciar.)
    """

    @classmethod
    def get_suggestion_for_user(cls, user):
        # Si no hay miembro vinculado, no sugerimos nada
        if not hasattr(user, "miembro") or not user.miembro:
            return None

        miembo = user.miembro
        hoy = timezone.now()

        # 1) Unidades donde el miembro es liderazgo
        unidades_ids = (
            UnidadCargo.objects.filter(
                miembo=miembo,
                rol__tipo="LIDERAZGO",  # si tu campo/valor difiere, lo ajustamos en el siguiente paso
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