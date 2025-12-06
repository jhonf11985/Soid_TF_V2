from django.db import models





class Votacion(models.Model):
    # -----------------------------
    # 1) Datos básicos
    # -----------------------------
    TIPO_VOTACION_CHOICES = [
        ("DIACONOS", "Diáconos"),
        ("LIDERES", "Líderes"),
        ("JUNTA", "Junta directiva"),
        ("MINISTERIOS", "Ministerios"),
        ("ESPECIAL", "Votación especial"),
        ("ENCUESTA", "Encuesta"),
    ]

    ESTADO_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("ABIERTA", "Abierta para votar"),
        ("CERRADA", "Cerrada"),
    ]

    # -----------------------------
    # Reglas de votación oficiales (La 1 a La 6)
    # -----------------------------
    REGLA_GANADOR_CHOICES = [
        ("LA1", "La 1 · Mayoría absoluta secuencial (50% + 1)"),
        ("LA2", "La 2 · Mayoría adaptativa (umbral recalculado)"),
        ("LA3", "La 3 · Mayoría 50%+1 y los demás por orden de votos"),
        ("LA4", "La 4 · TOP N (los más votados)"),
        ("LA5", "La 5 · Segunda vuelta (dos más votados)"),
        ("LA6", "La 6 · Mayoría especial (2/3 o 3/4)"),
    ]

    nombre = models.CharField(
        max_length=150,
        help_text="Ejemplo: 'Elección de diáconos 2026'.",
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción opcional de la votación."
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_VOTACION_CHOICES,
        default="DIACONOS",
    )

    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default="BORRADOR",
        help_text="Controla si la votación está abierta en el modo kiosko.",
    )

    
    # ¿Se permite mostrar el conteo en vivo en la pantalla pública
    # mientras la votación está ABIERTA?
    mostrar_conteo_en_vivo = models.BooleanField(
        default=False,
        help_text=(
            "Si está marcado, la pantalla pública mostrará el conteo de votos "
            "en tiempo real mientras la votación esté ABIERTA. "
            "Si no, solo se verán los candidatos y los resultados aparecerán "
            "cuando la votación se cierre."
        ),
    )

    # 2) Parámetros de quórum y asistencia

    # Miembros con derecho a voto (snapshot automático)
    total_habilitados = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Miembros con derecho a voto para esta elección (calculado automáticamente).",
    )

    # Miembros presentes físicamente ese día
    miembros_presentes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Número de miembros con derecho a voto que están presentes físicamente.",
    )

    TIPO_QUORUM_CHOICES = [
        ("PORCENTAJE", "Porcentaje de presentes"),
        ("CANTIDAD", "Cantidad fija de personas"),
    ]

    # 2) Parámetros de quórum y asistencia

    # Miembros con derecho a voto (snapshot automático)
    total_habilitados = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Miembros con derecho a voto para esta elección (calculado automáticamente).",
    )

    # Miembros presentes físicamente ese día
    miembros_presentes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Número de miembros con derecho a voto que están presentes físicamente.",
    )

    # Sobre qué base se calcula el quórum
    BASE_QUORUM_CHOICES = [
        ("HABILITADOS", "Sobre total de habilitados"),
        ("PRESENTES", "Sobre miembros presentes"),
    ]

    base_quorum = models.CharField(
        max_length=20,
        choices=BASE_QUORUM_CHOICES,
        default="HABILITADOS",
        help_text="Indica si el quórum se calcula usando el total de habilitados o solo los presentes.",
    )

    TIPO_QUORUM_CHOICES = [
        ("PORCENTAJE", "Porcentaje sobre la base"),
        ("CANTIDAD", "Cantidad fija de personas"),
    ]

    # Cómo se define el quórum: por porcentaje o por cantidad
    tipo_quorum = models.CharField(
        max_length=20,
        choices=TIPO_QUORUM_CHOICES,
        default="PORCENTAJE",
        help_text="Define si el quórum se calcula por porcentaje o por cantidad fija sobre la base elegida.",
    )

    # Valor del quórum:
    # - Si es porcentual: 50, 60, 75...
    # - Si es cantidad: número de personas (ej. 80)
    valor_quorum = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Si el quórum es porcentual, representa el porcentaje (ej. 50). Si es cantidad, el número de personas.",
    )

    # Votos mínimos requeridos para validar la votación (snapshot calculado)
    votos_minimos_requeridos = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Número de votos mínimos requeridos para que la votación sea válida.",
    )


    # -----------------------------
    # 3) Reglas para decidir ganadores
    # -----------------------------
    regla_ganador = models.CharField(
        max_length=20,
        choices=REGLA_GANADOR_CHOICES,
        default="LA1",
        help_text="Regla que define cómo se escogen los ganadores.",
    )

    numero_cargos = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Cantidad de cargos a elegir (ej. 3 diáconos, 2 líderes, etc.).",
    )

    edad_minima_candidato = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Edad mínima para ser candidato en esta elección (ej. 18 años).",
    )

    permite_empates = models.BooleanField(
        default=True,
        help_text="Si está desmarcado, luego se deberá gestionar el desempate.",
    )

    # -----------------------------
    # 4) Fechas y control generales
    # -----------------------------
    fecha_inicio = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha/hora de referencia para la votación (opcional).",
    )
    fecha_fin = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha/hora de referencia de cierre (opcional).",
    )

    # -----------------------------
    # 5) Parámetros de kiosko / remoto
    # -----------------------------
    permite_voto_remoto = models.BooleanField(
        default=False,
        help_text="Si está activo, se podrá habilitar voto remoto en el futuro.",
    )
    observaciones_internas = models.TextField(
        blank=True,
        help_text="Notas internas para el comité de votación (no se muestran al público).",
    )

    # -----------------------------
    # 6) Auditoría
    # -----------------------------
    creada_el = models.DateTimeField(auto_now_add=True)
    actualizada_el = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Votación"
        verbose_name_plural = "Votaciones"
        ordering = ["-creada_el"]

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

    # Propiedad útil para reportes
    @property
    def total_votos_emitidos(self):
        return self.votos.count()

    @property
    def quorom_alcanzado(self):
        """
        Devuelve True si se ha alcanzado el quórum definido.
        Si no hay quórum mínimo definido, devuelve None.
        """
        if self.votos_minimos_requeridos is None:
            return None
        return self.total_votos_emitidos >= (self.votos_minimos_requeridos or 0)


class Ronda(models.Model):
    """
    Representa una 'vuelta' dentro de una votación.
    Opción 1: se crea siempre una primera vuelta automática
    y luego se pueden añadir segundas vueltas desde la configuración.
    """
    ESTADO_RONDA_CHOICES = Votacion.ESTADO_CHOICES

    votacion = models.ForeignKey(
        Votacion,
        on_delete=models.CASCADE,
        related_name="rondas",
    )
    numero = models.PositiveIntegerField(
        default=1,
        help_text="1 = primera vuelta, 2 = segunda vuelta, etc.",
    )
    nombre = models.CharField(
        max_length=150,
        blank=True,
        help_text="Nombre opcional de la vuelta (ej.: 'Primera vuelta').",
    )
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_RONDA_CHOICES,
        default="BORRADOR",
    )
    fecha_inicio = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha/hora real de inicio de esta vuelta (opcional).",
    )
    fecha_fin = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha/hora real de cierre de esta vuelta (opcional).",
    )

    class Meta:
        verbose_name = "Vuelta"
        verbose_name_plural = "Vueltas"
        ordering = ["numero"]

    def __str__(self):
        etiqueta = self.nombre or f"Vuelta {self.numero}"
        return f"{etiqueta} - {self.votacion.nombre}"

class Candidato(models.Model):
    votacion = models.ForeignKey(
        Votacion,
        on_delete=models.CASCADE,
        related_name="candidatos",
    )
    miembro = models.ForeignKey(
        "miembros_app.Miembro",
        on_delete=models.PROTECT,
        related_name="candidaturas",
        null=True,
        blank=True,
        help_text="Miembro que es candidato en esta elección.",
    )
    nombre = models.CharField(
        max_length=150,
        help_text="Nombre del candidato (se puede rellenar automáticamente desde el miembro)."
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Información adicional del candidato (opcional)."
    )
    orden = models.PositiveIntegerField(
        default=0,
        help_text="Orden en que aparecerá en la lista (0 = sin orden específico).",
    )
    activo = models.BooleanField(
        default=True,
        help_text="Si está desmarcado, el candidato no se muestra para votar.",
    )

    class Meta:
        verbose_name = "Candidato"
        verbose_name_plural = "Candidatos"
        ordering = ["orden", "nombre"]

    def __str__(self):
        if self.miembro:
            return f"{self.nombre} (miembro #{self.miembro_id}) - {self.votacion.nombre}"
        return f"{self.nombre} - {self.votacion.nombre}"


class Voto(models.Model):
    votacion = models.ForeignKey(
        Votacion,
        on_delete=models.CASCADE,
        related_name="votos",
    )
    ronda = models.ForeignKey(
        Ronda,
        on_delete=models.PROTECT,
        related_name="votos",
        null=True,
        blank=True,
        help_text="Vuelta en la que se emitió este voto.",
    )
    miembro = models.ForeignKey(
        "miembros_app.Miembro",
        on_delete=models.PROTECT,
        related_name="votos",
        help_text="Miembro que emitió el voto.",
    )
    candidato = models.ForeignKey(
        Candidato,
        on_delete=models.PROTECT,
        related_name="votos",
    )
    tablet_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Identificador de la tablet o dispositivo (opcional).",
    )
    emitido_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Voto"
        verbose_name_plural = "Votos"
        ordering = ["-emitido_el"]
        constraints = [
            # Un miembro solo puede votar una vez en CADA VUELTA
            models.UniqueConstraint(
                fields=["ronda", "miembro"],
                name="un_voto_por_miembro_y_ronda",
            )
        ]

    def __str__(self):
        return f"Voto de {self.miembro_id} en {self.votacion.nombre}"
class ListaCandidatos(models.Model):
    ESTADO_BORRADOR = "BORRADOR"
    ESTADO_CONFIRMADA = "CONFIRMADA"

    ESTADO_CHOICES = [
        (ESTADO_BORRADOR, "Borrador"),
        (ESTADO_CONFIRMADA, "Confirmada"),
    ]

    nombre = models.CharField(
        max_length=150,
        help_text="Nombre de la lista, por ejemplo: 'Propuesta diáconos 2026'.",
    )
    codigo_lista = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True,
        help_text="Código opcional para identificar la lista (ej. LD-2026-01).",
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_BORRADOR,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(blank=True, null=True)
    notas = models.TextField(
        blank=True,
        help_text="Notas internas sobre esta lista (visible solo en el sistema).",
    )

    class Meta:
        verbose_name = "Lista de candidatos"
        verbose_name_plural = "Listas de candidatos"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        if self.codigo_lista:
            return f"{self.nombre} ({self.codigo_lista})"
        return self.nombre


class ListaCandidatosItem(models.Model):
    lista = models.ForeignKey(
        ListaCandidatos,
        on_delete=models.CASCADE,
        related_name="items",
    )
    miembro = models.ForeignKey(
        "miembros_app.Miembro",
        on_delete=models.PROTECT,
        related_name="listas_candidatos",
    )
    orden = models.PositiveIntegerField(
        default=0,
        help_text="Orden opcional para mostrar esta lista.",
    )
    observacion = models.CharField(
        max_length=200,
        blank=True,
        help_text="Observación opcional sobre este candidato en esta lista.",
    )

    class Meta:
        verbose_name = "Elemento de lista de candidatos"
        verbose_name_plural = "Elementos de listas de candidatos"
        ordering = ["orden", "miembro__apellidos", "miembro__nombres"]
        unique_together = ("lista", "miembro")

    def __str__(self):
        return f"{self.miembro} en {self.lista}"
