from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models


class QrToken(models.Model):
    token = models.CharField(max_length=64, unique=True, db_index=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField(null=True, blank=True)

    # Por ahora lo dejamos así para no depender de tu modelo real.
    # En el siguiente paso lo vinculamos a Miembro con ForeignKey real.
   

    # ✅ Vinculación real al miembro
    miembro = models.OneToOneField(
        "miembros_app.Miembro",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="qr_token",
    )
    def __str__(self):
        return f"{self.token}"


class QrScanLog(models.Model):
    token = models.ForeignKey(QrToken, on_delete=models.CASCADE, related_name="scans")
    escaneado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    modo = models.CharField(max_length=30, default="general")  # asistencia / perfil / evento
    resultado = models.CharField(max_length=30, default="ok")  # ok / invalido / expirado / inactivo
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.token.token} - {self.modo} - {self.resultado}"
