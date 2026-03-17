# notificaciones_app/motor.py

from dataclasses import dataclass
from typing import Callable, Dict, Any, List, Optional

from tenants.models import Tenant


@dataclass
class MotorResultado:
    nombre: str
    ok: bool
    detalle: Dict[str, Any]


# Cada task recibe tenant y devuelve un dict con estadísticas, o lanza excepción si falla.
TaskFn = Callable[[Tenant], Dict[str, Any]]

_TASKS: List[tuple[str, TaskFn]] = []


def registrar_task(nombre: str, fn: TaskFn) -> None:
    """
    Registra una tarea para el motor de notificaciones.
    La función debe aceptar un parámetro `tenant`.
    """
    _TASKS.append((nombre, fn))


def ejecutar_motor(tenant: Optional[Tenant] = None) -> List[MotorResultado]:
    """
    Ejecuta todas las tareas registradas para un tenant específico.
    
    Args:
        tenant: Tenant para el cual ejecutar las tareas.
                Si es None, no se ejecuta nada (por seguridad).
    
    Returns:
        Lista de resultados de cada tarea.
    """
    resultados: List[MotorResultado] = []
    
    if tenant is None:
        return resultados

    for nombre, fn in _TASKS:
        try:
            detalle = fn(tenant) or {}
            resultados.append(MotorResultado(nombre=nombre, ok=True, detalle=detalle))
        except Exception as e:
            resultados.append(MotorResultado(nombre=nombre, ok=False, detalle={"error": str(e)}))

    return resultados


# ============================================================
# Registrar tareas
# ============================================================
# NOTA: Cada tarea debe actualizarse para recibir `tenant` como parámetro.
# Ejemplo: def task_recordatorios_agenda(tenant: Tenant) -> Dict[str, Any]:

from agenda_app.cron import task_recordatorios_agenda
registrar_task("recordatorios_agenda", task_recordatorios_agenda)