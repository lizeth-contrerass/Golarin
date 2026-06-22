import os
from django.db import models
from django.conf import settings

# Función para enrutar el archivo a su carpeta correspondiente
def ruta_guardado_dataset(instance, filename):
    if instance.algoritmo == 'KNN':
        return f'datasets_csv/knn/{filename}'
    elif instance.algoritmo == 'NB':
        return f'datasets_csv/naivebayes/{filename}'
    return f'datasets_csv/otros/{filename}'

class Dataset(models.Model):
    TIPOS_ALGORITMO = [
        ('NB', 'Naive Bayes'),
        ('KNN', 'k-Nearest Neighbors'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nombre_archivo = models.CharField(max_length=150)
    # Nuevo campo para vincular el dataset a un algoritmo específico
    algoritmo = models.CharField(max_length=3, choices=TIPOS_ALGORITMO, default='KNN')
    # Usamos la función en el upload_to
    archivo = models.FileField(upload_to=ruta_guardado_dataset)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_algoritmo_display()} - {self.nombre_archivo}"