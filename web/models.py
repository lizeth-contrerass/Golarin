from django.db import models
from django.conf import settings  # Para conectar con tu modelo de Usuario personalizado


class Dataset(models.Model):
    # settings.AUTH_USER_MODEL apunta al modelo que creaste en la app 'usuarios'
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nombre_archivo = models.CharField(max_length=150)
    # FileField guarda el archivo físico en una carpeta llamada 'datasets_csv' dentro de tu MEDIA_ROOT
    archivo = models.FileField(upload_to='datasets_csv/')
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre_archivo


class ModeloML(models.Model):
    TIPOS_ALGORITMO = [
        ('NB', 'Naive Bayes'),
        ('KNN', 'k-Nearest Neighbors'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    tipo_algoritmo = models.CharField(max_length=3, choices=TIPOS_ALGORITMO)
    parametro_k = models.IntegerField(null=True, blank=True)  # Quedará nulo si el algoritmo es Naive Bayes
    fecha_entrenamiento = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # get_tipo_algoritmo_display() muestra el nombre completo en lugar de la abreviatura
        return f"{self.get_tipo_algoritmo_display()} - {self.dataset.nombre_archivo}"


class Prediccion(models.Model):
    RESULTADOS = [
        ('1', 'Victoria Local'),
        ('X', 'Empate'),
        ('2', 'Victoria Visitante'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    modelo = models.ForeignKey(ModeloML, on_delete=models.CASCADE)
    equipo_local = models.CharField(max_length=100)
    equipo_visitante = models.CharField(max_length=100)
    prob_local = models.DecimalField(max_digits=5, decimal_places=2)
    prob_empate = models.DecimalField(max_digits=5, decimal_places=2)
    prob_visitante = models.DecimalField(max_digits=5, decimal_places=2)
    resultado_predicho = models.CharField(max_length=1, choices=RESULTADOS)
    fecha_prediccion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.equipo_local} vs {self.equipo_visitante} -> {self.resultado_predicho}"


class Parley(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # ManyToManyField le dice a Django que cree la tabla intermedia automáticamente
    predicciones = models.ManyToManyField(Prediccion)
    probabilidad_combinada = models.DecimalField(max_digits=5, decimal_places=2)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Parley {self.id} - Prob: {self.probabilidad_combinada}%"