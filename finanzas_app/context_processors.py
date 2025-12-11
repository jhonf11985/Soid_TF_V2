# finanzas_app/context_processors.py

from django.db.models import Sum, Q
from decimal import Decimal
import datetime


def finanzas_sidebar_context(request):
    """
    Proporciona datos del resumen financiero del mes actual
    para mostrar en el sidebar de finanzas.
    """
    # Solo procesar si el usuario está autenticado
    if not request.user.is_authenticated:
        return {}
    
    # Solo procesar si estamos en una URL de finanzas
    if not request.path.startswith('/finanzas'):
        return {}
    
    try:
        from .models import MovimientoFinanciero
        
        hoy = datetime.date.today()
        
        # Totales del mes actual
        totales = MovimientoFinanciero.objects.filter(
            fecha__year=hoy.year,
            fecha__month=hoy.month
        ).exclude(estado="anulado").aggregate(
            ingresos=Sum("monto", filter=Q(tipo="ingreso")),
            egresos=Sum("monto", filter=Q(tipo="egreso")),
        )
        
        ingresos = totales.get("ingresos") or Decimal("0")
        egresos = totales.get("egresos") or Decimal("0")
        
        return {
            "resumen_sidebar": {
                "ingresos": ingresos,
                "egresos": egresos,
                "balance": ingresos - egresos,
            }
        }
    except Exception:
        return {
            "resumen_sidebar": {
                "ingresos": Decimal("0"),
                "egresos": Decimal("0"),
                "balance": Decimal("0"),
            }
        }