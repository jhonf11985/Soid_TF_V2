# notificaciones_app/motor.py
from dataclasses import dataclass
from typing import Callable, Dict, Any, List


@dataclass
class MotorResultado:
    nombre: str
    ok: bool
    detalle: Dict[str, Any]


# Cada task devuelve un dict con estadísticas, o lanza excepción si falla.
TaskFn = Callable[[], Dict[str, Any]]

_TASKS: List[tuple[str, TaskFn]] = []


def registrar_task(nombre: str, fn: TaskFn) -> None:
    _TASKS.append((nombre, fn))


def ejecutar_motor() -> List[MotorResultado]:
    resultados: List[MotorResultado] = []

    for nombre, fn in _TASKS:
        try:
            detalle = fn() or {}
            resultados.append(MotorResultado(nombre=nombre, ok=True, detalle=detalle))
        except Exception as e:
            resultados.append(MotorResultado(nombre=nombre, ok=False, detalle={"error": str(e)}))

    return resultados
