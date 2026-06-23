import os
from django.db import models
from django.conf import settings


# Función para enrutar el archivo a su carpeta correspondiente
def ruta_guardado_dataset(instance, filename):
    if instance.tipo == 'predeterminado':
        return f'datasets_csv/predeterminados/{filename}'
    if instance.algoritmo == 'NB':
        return f'datasets_csv/naivebayes/{filename}'
    return f'datasets_csv/otros/{filename}'


class Dataset(models.Model):
    TIPOS_ALGORITMO = [
        ('NB', 'Naive Bayes'),
    ]

    TIPOS_DATASET = [
        ('propio', 'Propio'),
        ('predeterminado', 'Predeterminado'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    nombre_archivo = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=TIPOS_DATASET, default='propio')
    algoritmo = models.CharField(max_length=3, choices=TIPOS_ALGORITMO, default='NB')
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

    # ESTE ES EL __STR__ DE DATASET (DEBE IR AQUÍ)
    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.get_algoritmo_display()} - {self.nombre_archivo}"


class Parlay(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    dataset = models.ForeignKey(Dataset, on_delete=models.SET_NULL, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Guardamos los partidos agregados en formato JSON
    partidos_data = models.JSONField(default=list)

    # ESTE ES EL __STR__ DE PARLAY
    def __str__(self):
        return f"Parlay #{self.id} - {self.usuario.username} ({self.fecha_creacion.strftime('%d/%m/%Y')})"