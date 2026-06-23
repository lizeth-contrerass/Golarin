import os
from django.db import models
from django.conf import settings

# Función para enrutar el archivo a su carpeta correspondiente
def ruta_guardado_dataset(instance, filename):
    if instance.algoritmo == 'NB':
        return f'datasets_csv/naivebayes/{filename}'
    return f'datasets_csv/otros/{filename}'

class Dataset(models.Model):
    TIPOS_ALGORITMO = [
        ('NB', 'Naive Bayes'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nombre_archivo = models.CharField(max_length=150)
    # Nuevo campo para vincular el dataset a un algoritmo específico
    algoritmo = models.CharField(max_length=3, choices=TIPOS_ALGORITMO, default='KNN')
    # Usamos la función en el upload_to
    archivo = models.FileField(upload_to=ruta_guardado_dataset)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    # --- METADATA GENERAL Y MÉTRICAS DE RESUSTITUCIÓN ---
    procesado = models.BooleanField(default=False)
    col_clases = models.CharField(max_length=100, blank=True, null=True)
    clases = models.JSONField(default=list, blank=True)
    cols_caracteristicas = models.JSONField(default=list, blank=True)
    cols_discretas = models.JSONField(default=list, blank=True)
    cols_continuas = models.JSONField(default=list, blank=True)
    valores_caracteristicas = models.JSONField(default=dict, blank=True)

    # Métricas obtenidas por resustitución
    accuracy = models.FloatField(blank=True, null=True)
    error = models.FloatField(blank=True, null=True)
    precision = models.FloatField(blank=True, null=True)
    recall = models.FloatField(blank=True, null=True)
    especificidad = models.FloatField(blank=True, null=True)

    # --- CAMPOS ESPECÍFICOS PARA NAIVE BAYES ---
    nb_probabilidades_clases = models.JSONField(default=dict, blank=True)
    nb_probabilidades_condicionales = models.JSONField(default=dict, blank=True)
    nb_parametros_cont = models.JSONField(default=dict, blank=True)


    def __str__(self):
        return f"{self.get_algoritmo_display()} - {self.nombre_archivo}"