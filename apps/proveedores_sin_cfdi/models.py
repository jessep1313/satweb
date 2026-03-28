from django.db import models

class ProveedorSinCfdi(models.Model):
    # Todos los campos definidos según la estructura proporcionada
    id = models.AutoField(primary_key=True)
    NombreComercial = models.CharField(max_length=255, null=True, blank=True)
    RazonSocial = models.CharField(max_length=255, null=True, blank=True)
    RFC = models.CharField(max_length=255, null=True, blank=True)
    Estatus = models.CharField(max_length=255, null=True, blank=True)
    tipoProveedor = models.CharField(max_length=255, null=True, blank=True)
    Contacto = models.CharField(max_length=255, null=True, blank=True)
    Planta = models.CharField(max_length=255, null=True, blank=True)
    Correo = models.CharField(max_length=255, null=True, blank=True)
    Correo2 = models.CharField(max_length=255, null=True, blank=True)
    Correo3 = models.CharField(max_length=255, null=True, blank=True)
    nombre = models.CharField(max_length=255, null=True, blank=True)
    apellidoPaterno = models.CharField(max_length=255, null=True, blank=True)
    apellidoMaterno = models.CharField(max_length=255, null=True, blank=True)
    tipoPersona = models.CharField(max_length=255, null=True, blank=True)
    codigoPostal = models.CharField(max_length=255, null=True, blank=True)
    calle = models.CharField(max_length=255, null=True, blank=True)
    noInt = models.CharField(max_length=255, null=True, blank=True)
    noExt = models.CharField(max_length=255, null=True, blank=True)
    colonia = models.CharField(max_length=255, null=True, blank=True)
    estado = models.CharField(max_length=255, null=True, blank=True)
    municipio = models.CharField(max_length=255, null=True, blank=True)
    ciudad = models.CharField(max_length=255, null=True, blank=True)
    telefono = models.CharField(max_length=255, null=True, blank=True)
    constancia = models.IntegerField(default=0)
    fecha_constancia1 = models.DateField(null=True, blank=True)
    constancia2 = models.IntegerField(default=0)
    constancia2_nombre = models.CharField(max_length=255, null=True, blank=True)
    fecha_constancia2 = models.DateField(null=True, blank=True)
    constancia3 = models.IntegerField(default=0)
    constancia3_nombre = models.CharField(max_length=255, null=True, blank=True)
    fecha_constancia3 = models.DateField(null=True, blank=True)
    constancia4 = models.CharField(max_length=100, null=True, blank=True)
    constancia4_nombre = models.CharField(max_length=100, null=True, blank=True)
    fecha_constancia4 = models.DateField(null=True, blank=True)
    rfc_identy = models.CharField(max_length=255, null=True, blank=True)  # RFC del cliente propietario
    msjefos = models.IntegerField(default=0)
    url = models.TextField(null=True, blank=True)
    url2 = models.CharField(max_length=255, null=True, blank=True)
    consultado = models.IntegerField(default=0)
    ano_actual = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'proveedores_sin_cfdi'
        managed = True
        verbose_name = 'Proveedor sin CFDI'
        verbose_name_plural = 'Proveedores sin CFDI'