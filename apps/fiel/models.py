import os
from django.db import models
from django.utils import timezone
from usuarios_tenant.models import Usuario

def fiel_upload_path(instance, filename):
    """Genera ruta: fiel/<rfc_cliente>/<año>/<mes>/<dia>/<filename>"""
    now = timezone.now()
    return f"fiel/{instance.rfc_cliente}/{now.year}/{now.month}/{now.day}/{filename}"

class CargaFiel(models.Model):
    rfc_cliente = models.CharField(
        max_length=13,
        unique=True,
        help_text="RFC del cliente (único por empresa)"
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cargas_fiel',
        help_text="Usuario que realizó la carga (opcional)"
    )
    archivo_cer = models.FileField(upload_to=fiel_upload_path, help_text="Archivo .cer")
    archivo_key = models.FileField(upload_to=fiel_upload_path, help_text="Archivo .key")
    password = models.CharField(max_length=255, help_text="Contraseña cifrada")
    fecha_carga = models.DateTimeField(auto_now_add=True)
    estatus = models.CharField(
        max_length=20,
        choices=[
            ('pendiente', 'Pendiente de validar'),
            ('validado', 'Validado'),
            ('rechazado', 'Rechazado')
        ],
        default='pendiente'
    )
    usuario_login = models.CharField(max_length=150, blank=True, help_text="Login del usuario que cargó")

    class Meta:
        db_table = 'cargas_fiel'
        verbose_name = 'Carga FIEL'
        verbose_name_plural = 'Cargas FIEL'

    def __str__(self):
        return f"{self.rfc_cliente} - {self.fecha_carga}"