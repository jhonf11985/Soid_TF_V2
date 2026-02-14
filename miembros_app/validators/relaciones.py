# -*- coding: utf-8 -*-
"""
miembros_app/validators/relaciones.py

Validador centralizado para relaciones familiares.
Sistema de dos niveles:
  - Errores: Bloquean el guardado (situaciones imposibles)
  - Warnings: Alertan pero permiten continuar (situaciones inusuales)

Uso:
    from miembros_app.validators.relaciones import ValidadorRelacionFamiliar
    
    validador = ValidadorRelacionFamiliar(miembro, familiar, tipo_relacion)
    resultado = validador.validar()
    
    if not resultado['valid']:
        # Mostrar errores y no guardar
    elif resultado['warnings']:
        # Mostrar warnings y pedir confirmación
    else:
        # Todo OK, guardar
"""

from datetime import date
from django.db.models import Q


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES DE CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

# Diferencias de edad (en años)
EDAD_MINIMA_PADRE_HIJO = 10          # Error si menor
EDAD_WARNING_PADRE_HIJO = 14         # Warning si entre 10-14

EDAD_MINIMA_ABUELO_NIETO = 20        # Error si menor
EDAD_WARNING_ABUELO_NIETO = 30       # Warning si entre 20-30

EDAD_MINIMA_BISABUELO = 30           # Error si menor

EDAD_MINIMA_CONYUGE = 12             # Error si menor (infante/niño)
EDAD_WARNING_CONYUGE = 18            # Warning si entre 12-18

DIFERENCIA_CONYUGE_WARNING = 25      # Warning si diferencia > 25 años

DIFERENCIA_HERMANOS_WARNING = 25     # Warning si diferencia > 25 años

# Tipos de relación que implican jerarquía generacional
TIPOS_ASCENDIENTES = {"padre", "madre", "abuelo", "bisabuelo"}
TIPOS_DESCENDIENTES = {"hijo", "nieto", "bisnieto"}
TIPOS_MISMA_GENERACION = {"hermano", "primo", "conyuge", "cunado"}


# ═══════════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class ValidadorRelacionFamiliar:
    """
    Valida una relación familiar antes de guardarla.
    
    Atributos:
        miembro: Miembro principal (quien tiene la relación)
        familiar: El familiar relacionado
        tipo_relacion: Tipo de relación (padre, madre, hijo, conyuge, etc.)
        relacion_id: ID de la relación si es edición (para excluir de duplicados)
    """
    
    def __init__(self, miembro, familiar, tipo_relacion, relacion_id=None):
        self.miembro = miembro
        self.familiar = familiar
        self.tipo_relacion = tipo_relacion
        self.relacion_id = relacion_id
        
        # Resultados
        self.errors = []
        self.warnings = []
        
        # Cache de edades
        self._edad_miembro = None
        self._edad_familiar = None
    
    # ───────────────────────────────────────────────────────────────────────────
    # PROPIEDADES AUXILIARES
    # ───────────────────────────────────────────────────────────────────────────
    
    @property
    def edad_miembro(self):
        """Edad del miembro principal (cacheada)."""
        if self._edad_miembro is None:
            self._edad_miembro = self._calcular_edad(self.miembro)
        return self._edad_miembro
    
    @property
    def edad_familiar(self):
        """Edad del familiar (cacheada)."""
        if self._edad_familiar is None:
            self._edad_familiar = self._calcular_edad(self.familiar)
        return self._edad_familiar
    
    @property
    def diferencia_edad(self):
        """Diferencia de edad (miembro - familiar). Positivo si miembro es mayor."""
        if self.edad_miembro is None or self.edad_familiar is None:
            return None
        return self.edad_miembro - self.edad_familiar
    
    @property
    def diferencia_edad_abs(self):
        """Diferencia de edad absoluta."""
        diff = self.diferencia_edad
        return abs(diff) if diff is not None else None
    
    # ───────────────────────────────────────────────────────────────────────────
    # MÉTODOS AUXILIARES
    # ───────────────────────────────────────────────────────────────────────────
    
    def _calcular_edad(self, miembro):
        """Calcula la edad de un miembro."""
        if not miembro or not miembro.fecha_nacimiento:
            return None
        hoy = date.today()
        nacimiento = miembro.fecha_nacimiento
        edad = hoy.year - nacimiento.year
        if (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day):
            edad -= 1
        return edad
    
    def _norm_genero(self, genero):
        """Normaliza el género a 'm' o 'f'."""
        g = (genero or "").strip().lower()
        if g in ("m", "masculino", "hombre"):
            return "m"
        if g in ("f", "femenino", "mujer"):
            return "f"
        return ""
    
    def _nombre_completo(self, miembro):
        """Retorna el nombre completo de un miembro."""
        return f"{miembro.nombres} {miembro.apellidos}".strip()
    
    def _get_relaciones_existentes(self):
        """Obtiene las relaciones existentes entre miembro y familiar."""
        from miembros_app.models import MiembroRelacion
        
        qs = MiembroRelacion.objects.filter(
            Q(miembro=self.miembro, familiar=self.familiar) |
            Q(miembro=self.familiar, familiar=self.miembro)
        )
        
        # Excluir la relación actual si es edición
        if self.relacion_id:
            qs = qs.exclude(pk=self.relacion_id)
        
        return list(qs)
    
    def _contar_padres(self, miembro):
        """Cuenta cuántos padres tiene un miembro."""
        from miembros_app.models import MiembroRelacion
        
        # Relaciones donde el miembro dice "X es mi padre/madre"
        como_hijo = MiembroRelacion.objects.filter(
            miembro=miembro,
            tipo_relacion__in=["padre", "madre"]
        ).count()
        
        # Relaciones donde alguien dice "miembro es mi hijo"
        como_padre = MiembroRelacion.objects.filter(
            familiar=miembro,
            tipo_relacion="hijo"
        ).count()
        
        return como_hijo + como_padre
    
    # ───────────────────────────────────────────────────────────────────────────
    # VALIDACIONES BÁSICAS
    # ───────────────────────────────────────────────────────────────────────────
    
    def _validar_auto_referencia(self):
        """Verifica que no sea auto-referencia."""
        if self.miembro.pk == self.familiar.pk:
            self.errors.append(
                "Una persona no puede ser familiar de sí misma."
            )
    
    def _validar_duplicados(self):
        """Verifica que no exista ya esta relación."""
        from miembros_app.models import MiembroRelacion
        
        relaciones = self._get_relaciones_existentes()
        
        for rel in relaciones:
            # Determinar el tipo efectivo desde la perspectiva del miembro
            if rel.miembro_id == self.miembro.pk:
                tipo_existente = rel.tipo_relacion
            else:
                tipo_existente = MiembroRelacion.inverse_tipo(
                    rel.tipo_relacion, 
                    self.miembro.genero
                )
            
            if tipo_existente == self.tipo_relacion:
                self.errors.append(
                    f"Ya existe una relación de tipo '{self.tipo_relacion}' "
                    f"entre {self._nombre_completo(self.miembro)} y "
                    f"{self._nombre_completo(self.familiar)}."
                )
                return
    
    # ───────────────────────────────────────────────────────────────────────────
    # VALIDACIONES DE EDAD - PADRE/MADRE/HIJO
    # ───────────────────────────────────────────────────────────────────────────
    
    def _validar_edad_padre_hijo(self):
        """Valida coherencia de edad para relaciones padre/madre/hijo."""
        if self.tipo_relacion not in ("padre", "madre", "hijo"):
            return
        
        if self.edad_miembro is None or self.edad_familiar is None:
            return  # No podemos validar sin fechas de nacimiento
        
        # Si el miembro dice "X es mi padre/madre"
        if self.tipo_relacion in ("padre", "madre"):
            # El familiar (padre/madre) debe ser MAYOR que el miembro
            if self.edad_familiar <= self.edad_miembro:
                self.errors.append(
                    f"{self._nombre_completo(self.familiar)} ({self.edad_familiar} años) "
                    f"no puede ser {self.tipo_relacion} de "
                    f"{self._nombre_completo(self.miembro)} ({self.edad_miembro} años) "
                    f"porque es menor o igual en edad."
                )
                return
            
            diferencia = self.edad_familiar - self.edad_miembro
            
            if diferencia < EDAD_MINIMA_PADRE_HIJO:
                self.errors.append(
                    f"La diferencia de edad ({diferencia} años) es muy pequeña. "
                    f"Un padre/madre debe tener al menos {EDAD_MINIMA_PADRE_HIJO} años "
                    f"más que su hijo/a."
                )
            elif diferencia < EDAD_WARNING_PADRE_HIJO:
                self.warnings.append(
                    f"La diferencia de edad ({diferencia} años) es inusualmente pequeña "
                    f"para una relación padre/madre-hijo. ¿Está seguro?"
                )
        
        # Si el miembro dice "X es mi hijo/a"
        elif self.tipo_relacion == "hijo":
            # El miembro (padre/madre) debe ser MAYOR que el familiar (hijo)
            if self.edad_miembro <= self.edad_familiar:
                self.errors.append(
                    f"{self._nombre_completo(self.miembro)} ({self.edad_miembro} años) "
                    f"no puede tener como hijo/a a "
                    f"{self._nombre_completo(self.familiar)} ({self.edad_familiar} años) "
                    f"porque es menor o igual en edad."
                )
                return
            
            diferencia = self.edad_miembro - self.edad_familiar
            
            if diferencia < EDAD_MINIMA_PADRE_HIJO:
                self.errors.append(
                    f"La diferencia de edad ({diferencia} años) es muy pequeña. "
                    f"Un padre/madre debe tener al menos {EDAD_MINIMA_PADRE_HIJO} años "
                    f"más que su hijo/a."
                )
            elif diferencia < EDAD_WARNING_PADRE_HIJO:
                self.warnings.append(
                    f"La diferencia de edad ({diferencia} años) es inusualmente pequeña "
                    f"para una relación padre/madre-hijo. ¿Está seguro?"
                )
    
    # ───────────────────────────────────────────────────────────────────────────
    # VALIDACIONES DE EDAD - ABUELO/NIETO
    # ───────────────────────────────────────────────────────────────────────────
    
    def _validar_edad_abuelo_nieto(self):
        """Valida coherencia de edad para relaciones abuelo/nieto."""
        if self.tipo_relacion not in ("abuelo", "nieto"):
            return
        
        if self.edad_miembro is None or self.edad_familiar is None:
            return
        
        # Si el miembro dice "X es mi abuelo/a"
        if self.tipo_relacion == "abuelo":
            if self.edad_familiar <= self.edad_miembro:
                self.errors.append(
                    f"{self._nombre_completo(self.familiar)} no puede ser abuelo/a de "
                    f"{self._nombre_completo(self.miembro)} porque es menor o igual en edad."
                )
                return
            
            diferencia = self.edad_familiar - self.edad_miembro
            
            if diferencia < EDAD_MINIMA_ABUELO_NIETO:
                self.errors.append(
                    f"La diferencia de edad ({diferencia} años) es muy pequeña para "
                    f"una relación abuelo/a-nieto/a. Se requieren al menos "
                    f"{EDAD_MINIMA_ABUELO_NIETO} años de diferencia."
                )
            elif diferencia < EDAD_WARNING_ABUELO_NIETO:
                self.warnings.append(
                    f"La diferencia de edad ({diferencia} años) es inusualmente pequeña "
                    f"para una relación abuelo/a-nieto/a. ¿Está seguro?"
                )
        
        # Si el miembro dice "X es mi nieto/a"
        elif self.tipo_relacion == "nieto":
            if self.edad_miembro <= self.edad_familiar:
                self.errors.append(
                    f"{self._nombre_completo(self.miembro)} no puede tener como nieto/a a "
                    f"{self._nombre_completo(self.familiar)} porque es menor o igual en edad."
                )
                return
            
            diferencia = self.edad_miembro - self.edad_familiar
            
            if diferencia < EDAD_MINIMA_ABUELO_NIETO:
                self.errors.append(
                    f"La diferencia de edad ({diferencia} años) es muy pequeña para "
                    f"una relación abuelo/a-nieto/a. Se requieren al menos "
                    f"{EDAD_MINIMA_ABUELO_NIETO} años de diferencia."
                )
            elif diferencia < EDAD_WARNING_ABUELO_NIETO:
                self.warnings.append(
                    f"La diferencia de edad ({diferencia} años) es inusualmente pequeña "
                    f"para una relación abuelo/a-nieto/a. ¿Está seguro?"
                )
    
    # ───────────────────────────────────────────────────────────────────────────
    # VALIDACIONES DE EDAD - CÓNYUGE
    # ───────────────────────────────────────────────────────────────────────────
    
    def _validar_edad_conyuge(self):
        """Valida coherencia de edad para relación de cónyuge."""
        if self.tipo_relacion != "conyuge":
            return
        
        # Validar edad mínima de ambos
        if self.edad_miembro is not None and self.edad_miembro < EDAD_MINIMA_CONYUGE:
            self.errors.append(
                f"{self._nombre_completo(self.miembro)} ({self.edad_miembro} años) "
                f"es demasiado joven para ser cónyuge."
            )
        
        if self.edad_familiar is not None and self.edad_familiar < EDAD_MINIMA_CONYUGE:
            self.errors.append(
                f"{self._nombre_completo(self.familiar)} ({self.edad_familiar} años) "
                f"es demasiado joven para ser cónyuge."
            )
        
        # Warnings para menores de edad
        if self.edad_miembro is not None:
            if EDAD_MINIMA_CONYUGE <= self.edad_miembro < EDAD_WARNING_CONYUGE:
                self.warnings.append(
                    f"{self._nombre_completo(self.miembro)} tiene {self.edad_miembro} años. "
                    f"¿Está seguro de registrar esta relación de cónyuge?"
                )
        
        if self.edad_familiar is not None:
            if EDAD_MINIMA_CONYUGE <= self.edad_familiar < EDAD_WARNING_CONYUGE:
                self.warnings.append(
                    f"{self._nombre_completo(self.familiar)} tiene {self.edad_familiar} años. "
                    f"¿Está seguro de registrar esta relación de cónyuge?"
                )
        
        # Warning por diferencia de edad grande
        if self.diferencia_edad_abs is not None:
            if self.diferencia_edad_abs > DIFERENCIA_CONYUGE_WARNING:
                self.warnings.append(
                    f"La diferencia de edad entre los cónyuges es de "
                    f"{self.diferencia_edad_abs} años. ¿Es correcto?"
                )
    
    # ───────────────────────────────────────────────────────────────────────────
    # VALIDACIONES DE EDAD - HERMANOS
    # ───────────────────────────────────────────────────────────────────────────
    
    def _validar_edad_hermano(self):
        """Valida coherencia de edad para relación de hermano."""
        if self.tipo_relacion != "hermano":
            return
        
        if self.diferencia_edad_abs is None:
            return
        
        if self.diferencia_edad_abs > DIFERENCIA_HERMANOS_WARNING:
            self.warnings.append(
                f"La diferencia de edad entre hermanos es de "
                f"{self.diferencia_edad_abs} años. Esto es inusual. ¿Es correcto?"
            )
    
    # ───────────────────────────────────────────────────────────────────────────
    # VALIDACIONES DE CONSISTENCIA
    # ───────────────────────────────────────────────────────────────────────────
    
    def _validar_consistencia_relaciones(self):
        """Valida que no existan relaciones contradictorias."""
        relaciones = self._get_relaciones_existentes()
        
        if not relaciones:
            return
        
        from miembros_app.models import MiembroRelacion
        
        tipos_existentes = set()
        for rel in relaciones:
            if rel.miembro_id == self.miembro.pk:
                tipos_existentes.add(rel.tipo_relacion)
            else:
                tipo_inverso = MiembroRelacion.inverse_tipo(
                    rel.tipo_relacion, 
                    self.miembro.genero
                )
                tipos_existentes.add(tipo_inverso)
        
        # Reglas de incompatibilidad
        incompatibilidades = {
            # Si ya es padre/madre, no puede ser hijo
            "padre": {"hijo", "nieto", "bisnieto"},
            "madre": {"hijo", "nieto", "bisnieto"},
            "hijo": {"padre", "madre", "abuelo", "bisabuelo"},
            
            # Si ya es cónyuge, no puede ser pariente directo
            "conyuge": {"padre", "madre", "hijo", "hermano", "abuelo", "nieto"},
            
            # Si ya es hermano, no puede ser padre/hijo
            "hermano": {"padre", "madre", "hijo"},
            
            # Abuelo/nieto
            "abuelo": {"hijo", "nieto", "bisnieto", "padre", "madre"},
            "nieto": {"padre", "madre", "abuelo", "bisabuelo"},
        }
        
        tipos_incompatibles = incompatibilidades.get(self.tipo_relacion, set())
        
        conflictos = tipos_existentes & tipos_incompatibles
        
        if conflictos:
            conflictos_str = ", ".join(conflictos)
            self.errors.append(
                f"No se puede crear la relación '{self.tipo_relacion}' porque "
                f"ya existe una relación incompatible ({conflictos_str}) entre "
                f"estas dos personas."
            )
    
    # ───────────────────────────────────────────────────────────────────────────
    # VALIDACIONES DE GÉNERO
    # ───────────────────────────────────────────────────────────────────────────
    
    def _validar_genero(self):
        """Valida coherencia de género para ciertos tipos de relación."""
        genero_familiar = self._norm_genero(self.familiar.genero)
        
        if not genero_familiar:
            return  # No hay género definido, no validar
        
        # El familiar es quien tiene el rol (padre, madre, etc.)
        if self.tipo_relacion == "padre" and genero_familiar == "f":
            self.warnings.append(
                f"{self._nombre_completo(self.familiar)} está registrado/a como género "
                f"femenino, pero se está asignando como 'Padre'. "
                f"¿Debería ser 'Madre'?"
            )
        
        elif self.tipo_relacion == "madre" and genero_familiar == "m":
            self.warnings.append(
                f"{self._nombre_completo(self.familiar)} está registrado/a como género "
                f"masculino, pero se está asignando como 'Madre'. "
                f"¿Debería ser 'Padre'?"
            )
    
    # ───────────────────────────────────────────────────────────────────────────
    # VALIDACIONES DE CANTIDAD
    # ───────────────────────────────────────────────────────────────────────────
    
    def _validar_cantidad_padres(self):
        """Valida que no se excedan los padres permitidos."""
        if self.tipo_relacion not in ("padre", "madre"):
            return
        
        padres_actuales = self._contar_padres(self.miembro)
        
        if padres_actuales >= 2:
            self.warnings.append(
                f"{self._nombre_completo(self.miembro)} ya tiene {padres_actuales} "
                f"padre(s)/madre(s) registrados. ¿Está seguro de agregar otro?"
            )
    
    # ───────────────────────────────────────────────────────────────────────────
    # MÉTODO PRINCIPAL
    # ───────────────────────────────────────────────────────────────────────────
    
    def validar(self):
        """
        Ejecuta todas las validaciones.
        
        Returns:
            dict: {
                'valid': bool,          # True si no hay errores
                'errors': list[str],    # Lista de errores (bloquean)
                'warnings': list[str],  # Lista de warnings (alertan)
            }
        """
        # Limpiar resultados previos
        self.errors = []
        self.warnings = []
        
        # Ejecutar validaciones en orden
        self._validar_auto_referencia()
        self._validar_duplicados()
        
        # Si hay errores básicos, no continuar
        if self.errors:
            return self._resultado()
        
        # Validaciones de edad
        self._validar_edad_padre_hijo()
        self._validar_edad_abuelo_nieto()
        self._validar_edad_conyuge()
        self._validar_edad_hermano()
        
        # Validaciones de consistencia
        self._validar_consistencia_relaciones()
        
        # Validaciones de género y cantidad
        self._validar_genero()
        self._validar_cantidad_padres()
        
        return self._resultado()
    
    def _resultado(self):
        """Construye el diccionario de resultado."""
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors.copy(),
            "warnings": self.warnings.copy(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN HELPER PARA USO RÁPIDO
# ═══════════════════════════════════════════════════════════════════════════════

def validar_relacion_familiar(miembro, familiar, tipo_relacion, relacion_id=None):
    """
    Función helper para validar rápidamente una relación.
    
    Args:
        miembro: Miembro principal
        familiar: El familiar
        tipo_relacion: Tipo de relación
        relacion_id: ID de la relación si es edición (opcional)
    
    Returns:
        dict: Resultado de la validación
    
    Ejemplo:
        resultado = validar_relacion_familiar(juan, maria, "conyuge")
        if not resultado['valid']:
            print(resultado['errors'])
    """
    validador = ValidadorRelacionFamiliar(
        miembro=miembro,
        familiar=familiar,
        tipo_relacion=tipo_relacion,
        relacion_id=relacion_id,
    )
    return validador.validar()