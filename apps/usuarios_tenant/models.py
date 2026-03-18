from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class UsuarioManager(BaseUserManager):
    def create_user(self, use_login, password=None, **extra_fields):
        if not use_login:
            raise ValueError('El nombre de usuario es obligatorio')
        user = self.model(use_login=use_login, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

class Usuario(AbstractBaseUser):
    use_id = models.AutoField(primary_key=True)
    use_login = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128, db_column='use_password')  # columna use_password
    use_email = models.EmailField(max_length=254, blank=True)
    use_nombre = models.CharField(max_length=255)
    use_rfc = models.CharField(max_length=13, blank=True)
    use_tipo = models.CharField(
        max_length=10,
        choices=[('Admin', 'Admin'), ('Cliente', 'Cliente')],
        default='Cliente'
    )
    is_active = models.BooleanField(default=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'use_login'
    REQUIRED_FIELDS = ['use_nombre', 'use_email']

    class Meta:
        db_table = 'users'
        managed = True

    def __str__(self):
        return f"{self.use_login} - {self.use_tipo}"