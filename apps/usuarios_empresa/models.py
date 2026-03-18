"""
Modelo para los usuarios tipo Empresa (superadmin global).
Almacenado en base de datos 'default'.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models

class UsuarioEmpresa(AbstractUser):
    """
    Usuario que administra las empresas (superadmin).
    Hereda de AbstractUser para tener los campos básicos:
    username, password, email, first_name, last_name, etc.
    """
    # Podemos agregar campos extra si se requieren, por ahora ninguno.
    class Meta:
        db_table = 'usuarios_empresa'  # Nombre de tabla explícito
        verbose_name = 'Usuario Empresa'
        verbose_name_plural = 'Usuarios Empresa'

    def __str__(self):
        return self.username