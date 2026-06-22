# usuarios/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    # Hereda username, email, password por defecto de Django
    # Agregamos nuestro campo personalizado:
    f_nacimiento = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.username