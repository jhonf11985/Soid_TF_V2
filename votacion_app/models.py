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

    REGLA_GANADOR_CHOICES = [
        ("MAYORIA_50_1", "Mayoría 50% + 1"),
        ("MAS_VOTOS", "Más votos (simple)"),
        ("TOP_N", "Top N más votados"),
        ("TOP_1_Y_2", "1er y 2do lugar"),
    ]
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

    # -----------------------------
    # 2) Parámetros de quórum
    # -----------------------------
    total_habilitados = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Número total de personas con derecho a voto para esta elección.",
    )
    quorum_minimo = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Número mínimo de votantes requeridos (quórum). Opcional.",
    )

    # -----------------------------
    # 3) Reglas para decidir ganadores
    # -----------------------------
    regla_ganador = models.CharField(
        max_length=20,
        choices=REGLA_GANADOR_CHOICES,
        default="MAYORIA_50_1",
        help_text="Regla que define cómo se escogen los ganadores.",
    )
    numero_cargos = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Cantidad de cargos a elegir (ej. 3 diáconos, 2 líderes, etc.).",
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
        if self.quorum_minimo is None:
            return None
        return self.total_votos_emitidos >= self.quorum_minimo


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
