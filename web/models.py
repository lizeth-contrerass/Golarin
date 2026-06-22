from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    # Campos que Django ya hereda automáticamente:
    # id (Autoincrementable), username, password, email, is_staff, is_superuser, is_active

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    f_nacimiento = models.DateField(null=True, blank=True)
    fecha_sesion = models.DateTimeField(auto_now=True) # Se actualiza automáticamente en cada login
    token = models.CharField(max_length=255, null=True, blank=True)
    estado = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.username} ({self.nombre} {self.apellido})"