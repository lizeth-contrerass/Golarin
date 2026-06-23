import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from web.models import Dataset

# Importamos las funciones analíticas reales de tu utilidad de Naive Bayes
from web.utils import (
    nb_prob_clases,
    nb_prob_cond_discreta,
    nb_parametros_continuos,
    verificar_naive_bayes,
    es_continuo
)


class Command(BaseCommand):
    help = 'Carga, entrena y procesa los datasets predeterminados en la base de datos calculando sus métricas'

    def handle(self, *args, **options):
        # Definimos los archivos predeterminados alojados en tu directorio media
        # Cambia la lista de datasets_a_cargar por esta forma estructurada:
        datasets_a_cargar = [
            {
                'nombre': 'Equipo ganador - MX',
                # Usamos os.path.join para evitar problemas de diagonales cruzadas
                'ruta_relativa': os.path.join('datasets_csv', 'naivebayes', 'determinarEquipoGanador.csv'),
                'algoritmo': 'NB'
            },
            {
                'nombre': 'Número de goles local - MX',
                # Usamos os.path.join para evitar problemas de diagonales cruzadas
                'ruta_relativa': os.path.join('datasets_csv', 'naivebayes', 'determinarNumeroGolesLocal.csv'),
                'algoritmo': 'NB'
            },
            {
                'nombre': 'Número de goles visitante - MX',
                # Usamos os.path.join para evitar problemas de diagonales cruzadas
                'ruta_relativa': os.path.join('datasets_csv', 'naivebayes', 'determinarNumeroGolesVisitante.csv'),
                'algoritmo': 'NB'
            },
        ]

        for ds_info in datasets_a_cargar:
            # 1. Comprobar si ya existe en la Base de Datos para evitar duplicaciones
            existe = Dataset.objects.filter(archivo=ds_info['ruta_relativa'], tipo='predeterminado').exists()

            if existe:
                self.stdout.write(self.style.WARNING(f"El dataset '{ds_info['nombre']}' ya está registrado."))
                continue

            # 2. Construir la ruta absoluta en disco
            ruta_absoluta = os.path.join(settings.MEDIA_ROOT, ds_info['ruta_relativa'])

            if not os.path.exists(ruta_absoluta):
                self.stdout.write(self.style.ERROR(f"Archivo físico no encontrado en: {ruta_absoluta}"))
                continue

            self.stdout.write(f"Procesando y entrenando Naive Bayes para: {ds_info['nombre']}...")

            try:
                # 3. Leer el archivo CSV con pandas
                df = pd.read_csv(ruta_absoluta)

                # Asumimos la estructura estándar de tu proyecto: [ID, caracteristicas..., Clase]
                col_clases = df.columns[-1]
                clases = df[col_clases].unique().tolist()
                cols_caracteristicas = df.columns[1:-1].tolist()

                # Separar dinámicamente columnas continuas y discretas analizando el primer registro disponible
                cols_continuas = []
                cols_discretas = []
                for col in cols_caracteristicas:
                    primer_valor = df[col].iloc[0]
                    if es_continuo(primer_valor):
                        cols_continuas.append(col)
                    else:
                        cols_discretas.append(col)

                # Formatear el diccionario general de valores únicos para las variables discretas
                valores_caracteristicas = {}
                for col in cols_discretas:
                    valores_caracteristicas[col] = [str(v).capitalize() for v in df[col].unique().tolist()]

                # 4. Procesar y calcular parámetros probabilísticos del entrenamiento (Métricas Fijas)
                prob_clases = nb_prob_clases(df, col_clases, clases)
                prob_cond = nb_prob_cond_discreta(df, cols_discretas, col_clases, clases)
                param_cont = nb_parametros_continuos(df, cols_continuas, col_clases, clases)

                # 5. Ejecutar la validación por resustitución sobre el dataset completo para obtener el rendimiento real
                acc, err, prec, rec, esp = verificar_naive_bayes(
                    df,
                    cols_caracteristicas,
                    col_clases,
                    clases,
                    prob_clases,
                    prob_cond,
                    param_cont,
                    cols_discretas,
                    cols_continuas
                )

                # 6. Guardar el registro completo en la Base de Datos con todos sus campos calculados
                Dataset.objects.create(
                    usuario=None,  # Pertenece al sistema global, por ende es nulo
                    nombre_archivo=ds_info['nombre'],
                    archivo=ds_info['ruta_relativa'],
                    tipo='predeterminado',
                    algoritmo=ds_info['algoritmo'],
                    procesado=True,

                    # Guardado de metadata estructural
                    col_clases=col_clases,
                    clases=[str(c) for c in clases],
                    cols_caracteristicas=cols_caracteristicas,
                    cols_discretas=cols_discretas,
                    cols_continuas=cols_continuas,
                    valores_caracteristicas=valores_caracteristicas,

                    # Guardado de métricas macro-average fijas
                    accuracy=acc,
                    error=err,
                    precision=prec,
                    recall=rec,
                    especificidad=esp,

                    # Guardado de la distribución de tablas de probabilidad calculadas
                    nb_probabilidades_clases=prob_clases,
                    nb_probabilidades_condicionales=prob_cond,
                    nb_parametros_cont=param_cont
                )

                self.stdout.write(
                    self.style.SUCCESS(f"Éxito: '{ds_info['nombre']}' entrenado y guardado permanentemente."))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error crítico procesando {ds_info['nombre']}: {e}"))