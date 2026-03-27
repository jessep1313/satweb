from django.db import models

class PeticionSat(models.Model):
    idpeticion = models.CharField(max_length=255, verbose_name="ID Petición")
    estatuspeticion = models.IntegerField(default=0, verbose_name="Estatus")  # 0: Pendiente
    fechainicio = models.DateField(verbose_name="Fecha inicio")
    fechafinal = models.DateField(verbose_name="Fecha final")
    rfc = models.CharField(max_length=100, verbose_name="RFC")
    CodEstatus = models.CharField(max_length=100, verbose_name="Código estatus SAT")
    Mensaje = models.CharField(max_length=255, verbose_name="Mensaje SAT")
    RfcSolicitante = models.CharField(max_length=100, verbose_name="RFC solicitante")
    cargadoxml = models.IntegerField(default=0, verbose_name="Cargado XML")
    tipo = models.CharField(max_length=255, default='R', verbose_name="Tipo")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'peticiones_sat'
        verbose_name = 'Petición SAT'
        verbose_name_plural = 'Peticiones SAT'

    def __str__(self):
        return f"{self.rfc} - {self.idpeticion}"