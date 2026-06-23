import os
import pandas as pd
import numpy as np
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm

from .forms import FormularioRegistro
from .models import Dataset

# Importación de las funciones de procesamiento matemático desde utils.py
from .utils import (
    es_continuo,
    nb_prob_clases,
    nb_prob_cond_discreta,
    nb_parametros_continuos,
    verificar_naive_bayes,
)

from django.http import JsonResponse
import json
from .utils import calcular_naive_bayes
from .models import Parlay

@login_required(login_url='login')
def nuevoParlay(request):
    usuario = request.user

    # 1. Manejo de peticiones AJAX (POST para calcular y guardar agrupados)
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            dataset_id = data.get('dataset_id')
            partidos_input = data.get('partidos', [])

            if not dataset_id or not partidos_input:
                return JsonResponse({'error': 'Información incompleta'}, status=400)

            dataset = Dataset.objects.get(id=dataset_id)
            ruta_csv = dataset.archivo.path
            df = pd.read_csv(ruta_csv)

            # Obtener el promedio de todas las variables continuas del dataset
            promedios_continuos = {}
            for col in dataset.cols_continuas:
                promedios_continuos[col] = float(df[col].astype(float).mean())

            prob_clases = dataset.nb_probabilidades_clases
            prob_cond = dataset.nb_probabilidades_condicionales
            param_cont = dataset.nb_parametros_cont

            partidos_calculados = []

            # Identificar dinámicamente qué columnas corresponden a Home y Away en cols_discretas
            col_home = dataset.cols_discretas[0]
            col_away = dataset.cols_discretas[1]

            for p in partidos_input:
                home_value = p.get('home')
                away_value = p.get('away')

                # Reconstruir el vector completo siguiendo el orden de cols_caracteristicas
                vector_entrada = []
                for col in dataset.cols_caracteristicas:
                    if col == col_home:
                        vector_entrada.append(home_value)
                    elif col == col_away:
                        vector_entrada.append(away_value)
                    elif col in dataset.cols_continuas:
                        vector_entrada.append(promedios_continuos[col])
                    else:
                        vector_entrada.append(None)

                # Inferencia Naive Bayes
                probs_brutas = calcular_naive_bayes(
                    vector_entrada, dataset.cols_caracteristicas, dataset.clases,
                    prob_clases, prob_cond, param_cont, dataset.cols_discretas, dataset.cols_continuas
                )

                # Normalización de probabilidades
                suma_probs = sum(probs_brutas.values())
                probs_normalizadas = {}
                if suma_probs > 0:
                    for k, v in probs_brutas.items():
                        probs_normalizadas[k] = round((v / suma_probs) * 100, 2)
                else:
                    for k in probs_brutas.keys():
                        probs_normalizadas[k] = round(100 / len(probs_brutas), 2)

                clase_ganadora = max(probs_normalizadas, key=probs_normalizadas.get)

                partidos_calculados.append({
                    'home': home_value,
                    'away': away_value,
                    'probabilidades': probs_normalizadas,
                    'ganador': clase_ganadora
                })

            # PERSISTENCIA AGRUPADA: Se crea una sola instancia de Parlay para toda la ronda.
            # Esto genera un único ID y un único campo 'fecha_creacion' (Timestamp) para todos estos partidos.
            parlay_obj = Parlay.objects.create(
                usuario=usuario,
                dataset=dataset,
                partidos_data=partidos_calculados
            )

            return JsonResponse({'status': 'success', 'resultados': partidos_calculados})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # 2. Manejo de peticiones AJAX (GET para cargar equipos dinámicamente)
    if request.method == 'GET' and request.GET.get('action') == 'get_equipos':
        ds_id = request.GET.get('dataset_id')
        try:
            dataset = Dataset.objects.get(id=ds_id)
            return JsonResponse({
                'cols_discretas': dataset.cols_discretas,
                'valores': dataset.valores_caracteristicas
            })
        except Dataset.DoesNotExist:
            return JsonResponse({'error': 'Dataset no encontrado'}, status=404)

    # 3. Carga inicial de la página
    datasets_disponibles = Dataset.objects.filter(procesado=True)
    return render(request, 'web/nuevoParlay.html', {'datasets_disponibles': datasets_disponibles})


import os
import pandas as pd
from django.shortcuts import render
from django.conf import settings
from .models import Dataset


@login_required(login_url='login')
def datasets(request):
    usuario = request.user if request.user.is_authenticated else None

    # ==========================================
    # PROCESAMIENTO CUANDO EL USUARIO SUBE UN CSV (POST)
    # ==========================================
    if request.method == 'POST':
        archivo_subido = request.FILES.get('archivo')
        if not archivo_subido:
            messages.error(request, "Por favor, selecciona un archivo CSV válido.")
            return redirect('datasets')

        try:
            # 1. Crear la instancia inicial del Dataset en la BD
            dataset = Dataset.objects.create(
                usuario=usuario,
                nombre_archivo=archivo_subido.name,
                tipo='propio',
                algoritmo='NB',
                archivo=archivo_subido
            )

            # 2. Leer el CSV para extraer e inferir metadata
            df = pd.read_csv(dataset.archivo.path)
            columnas_totales = df.columns.tolist()

            if len(columnas_totales) < 2:
                dataset.delete()
                messages.error(request, "El CSV debe contener al menos las columnas de equipos y la clase.")
                return redirect('datasets')

            # La última columna por convención matemática y de tu proyecto es la Clase
            col_clases = columnas_totales[-1]
            clases_encontradas = df[col_clases].dropna().unique().tolist()

            # Las demás columnas son potenciales características
            cols_caracteristicas = columnas_totales[:-1]

            cols_discretas_temp = []
            cols_continuas = []

            for col in cols_caracteristicas:
                # Si los valores no son numéricos, o tienen baja cardinalidad de texto, son discretos (equipos)
                primer_valor = df[col].dropna().iloc[0] if not df[col].dropna().empty else ""
                if not es_continuo(primer_valor):
                    cols_discretas_temp.append(col)
                else:
                    cols_continuas.append(col)

            # 3. CRUCIAL: Mapear y ordenar estrictamente [Home, Away] para que no se inviertan
            col_home = None
            col_away = None

            # Intentar identificar por palabras clave en el nombre de la columna
            for col in cols_discretas_temp:
                col_lower = col.lower()
                if 'home' in col_lower or 'local' in col_lower:
                    col_home = col
                elif 'away' in col_lower or 'visitante' in col_lower or 'visita' in col_lower:
                    col_away = col

            # Si no se identificaron por nombre, tomamos las primeras 2 discretas por orden posicional
            if not col_home and len(cols_discretas_temp) > 0:
                col_home = cols_discretas_temp[0]
            if not col_away and len(cols_discretas_temp) > 1:
                col_away = cols_discretas_temp[1]

            # Reestructurar la lista para garantizar el orden: [0] = Home, [1] = Away
            cols_discretas = []
            if col_home: cols_discretas.append(col_home)
            if col_away: cols_discretas.append(col_away)

            # Agregar cualquier otra discreta sobrante si existiera
            for col in cols_discretas_temp:
                if col != col_home and col != col_away:
                    cols_discretas.append(col)

            # Validar que cumpla con los requisitos mínimos de tu vista 'nuevoParlay'
            if len(cols_discretas) < 2:
                dataset.delete()
                messages.error(request, "No se pudieron identificar las 2 columnas categóricas para Local y Visitante.")
                return redirect('datasets')

            # 4. Construir diccionario de valores únicos estructurados por columna
            valores_caracteristicas = {}
            for col in cols_discretas:
                # Normalizamos capitalización de strings para homogeneidad en los selectores
                valores_unicos = df[col].dropna().astype(str).str.capitalize().unique().tolist()
                valores_caracteristicas[col] = sorted(valores_unicos)

            # 5. Entrenamiento y cálculo de probabilidades del Modelo de Naive Bayes
            prob_clases = nb_prob_clases(df, col_clases, clases_encontradas)
            prob_cond = nb_prob_cond_discreta(df, cols_discretas, col_clases, clases_encontradas)
            param_cont = nb_parametros_continuos(df, cols_continuas, col_clases, clases_encontradas)

            # 6. Cálculo de métricas por resustitución utilizando tu validador de macro-averaging
            acc, error, prec, rec, esp = verificar_naive_bayes(
                df, cols_caracteristicas, col_clases, clases_encontradas,
                prob_clases, prob_cond, param_cont, cols_discretas, cols_continuas
            )

            # 7. Persistir toda la metadata calculada en el objeto
            dataset.col_clases = col_clases
            dataset.clases = [str(c) for c in clases_encontradas]
            dataset.cols_caracteristicas = cols_caracteristicas
            dataset.cols_discretas = cols_discretas
            dataset.cols_continuas = cols_continuas
            dataset.valores_caracteristicas = valores_caracteristicas

            dataset.nb_probabilidades_clases = prob_clases
            dataset.nb_probabilidades_condicionales = prob_cond
            dataset.nb_parametros_cont = param_cont

            dataset.accuracy = acc
            dataset.error = error
            dataset.precision = prec
            dataset.recall = rec
            dataset.especificidad = esp
            dataset.procesado = True
            dataset.save()

            messages.success(request,
                             f"¡Dataset '{dataset.nombre_archivo}' subido, entrenado y procesado exitosamente!")
            return redirect('/datasets/?tipo=propio')

        except Exception as e:
            if 'dataset' in locals() and dataset.id:
                dataset.delete()
            messages.error(request, f"Error al procesar la estructura del dataset: {str(e)}")
            return redirect('datasets')

    # ==========================================
    # MANEJO DE RENDERIZADO VISUAL (GET)
    # ==========================================
    datasets_usuario = Dataset.objects.filter(usuario=usuario, tipo='propio', procesado=True)
    datasets_predeterminados = Dataset.objects.filter(tipo='predeterminado', procesado=True)

    id_seleccionado = request.GET.get('id_dataset')
    dataset_actual = None
    columnas = []
    partidos = []
    nombre_dataset = "Ninguno"

    if id_seleccionado:
        try:
            dataset_actual = Dataset.objects.get(id=id_seleccionado)
            nombre_dataset = dataset_actual.nombre_archivo
            ruta_csv = dataset_actual.archivo.path

            if os.path.exists(ruta_csv):
                df = pd.read_csv(ruta_csv)
                columnas = df.columns.tolist()
                partidos = df.head(10).values.tolist()
        except Dataset.DoesNotExist:
            pass

    context = {
        'datasets_usuario': datasets_usuario,
        'datasets_predeterminados': datasets_predeterminados,
        'id_seleccionado': id_seleccionado,
        'dataset_actual': dataset_actual,
        'columnas': columnas,
        'partidos': partidos,
        'nombre_dataset': nombre_dataset,
    }

    return render(request, 'web/datasets.html', context)


from django.core.paginator import Paginator


@login_required(login_url='login')
def historial(request):
    usuario = request.user

    # Obtener todas las rondas guardadas por este usuario, de la más reciente a la más antigua
    parlays_list = Parlay.objects.filter(usuario=usuario).order_index_by('-fecha_creacion') if hasattr(Parlay.objects,
                                                                                                       'order_index_by') else Parlay.objects.filter(
        usuario=usuario).order_by('-fecha_creacion')

    # Paginación: 10 grupos (instancias de Parlay) por página
    paginator = Paginator(parlays_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'web/historial.html', {'page_obj': page_obj})


def registro_vista(request):
    if request.user.is_authenticated:
        return redirect('inicio')

    if request.method == 'POST':
        form = FormularioRegistro(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"¡Bienvenido a Golarín, {user.first_name}!")
            return redirect('inicio')
    else:
        form = FormularioRegistro()
    return render(request, 'web/registro.html', {'form': form})


def login_vista(request):
    if request.user.is_authenticated:
        return redirect('inicio')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"¡Hola de nuevo, {user.username}!")
                return redirect('inicio')
            else:
                messages.error(request, "Usuario o contraseña incorrectos.")
        else:
            messages.error(request, "Información de inicio de sesión inválida.")
    else:
        form = AuthenticationForm()

    return render(request, 'web/login.html', {'form': form})


@login_required(login_url='login')
def logout_vista(request):
    logout(request)
    return redirect('index')


@login_required(login_url='login')
def inicio(request):
    usuario = request.user
    es_admin = usuario.is_staff or usuario.is_superuser

    # --- CONTADORES DE DATASETS ---
    datasets_propios = Dataset.objects.filter(usuario=usuario, tipo='propio').count()
    datasets_predeterminados = Dataset.objects.filter(tipo='predeterminado').count()
    total_datasets = datasets_propios + datasets_predeterminados

    # --- CONTADORES DE PARLAYS Y PARTIDOS ---
    all_parlays = Parlay.objects.filter(usuario=usuario)

    total_parlays_count = 0
    total_partidos_count = 0

    for p in all_parlays:
        # Si tiene más de un partido dentro del JSON, cuenta como parlay
        if len(p.partidos_data) > 1:
            total_parlays_count += 1
        else:
            total_partidos_count += 1

    suma_total_rondas = total_parlays_count + total_partidos_count

    # --- ÚLTIMOS 3 REGISTROS RECIENTES ---
    recientes = all_parlays.order_by('-fecha_creacion')[:3]

    context = {
        'es_admin': es_admin,
        'datasets_propios': datasets_propios,
        'datasets_predeterminados': datasets_predeterminados,
        'total_datasets': total_datasets,
        'total_parlays_count': total_parlays_count,
        'total_partidos_count': total_partidos_count,
        'suma_total_rondas': suma_total_rondas,
        'recientes': recientes,
    }
    return render(request, 'web/inicio.html', context)


@login_required(login_url='login')
def eliminar_dataset(request, id_dataset):
    if request.method == 'POST':
        try:
            dataset = Dataset.objects.get(id=id_dataset, usuario=request.user)
            if dataset.archivo and os.path.exists(dataset.archivo.path):
                os.remove(dataset.archivo.path)
            dataset.delete()

            messages.success(request, "Dataset eliminado correctamente.")
        except Dataset.DoesNotExist:
            messages.error(request, "El dataset no existe o no tienes permiso para eliminarlo.")
        except Exception as e:
            messages.error(request, f"Error al eliminar el dataset: {str(e)}")

    algo_actual = request.GET.get('algo', 'TODOS')
    return redirect(f'/datasets/?tipo=propio&algo={algo_actual}')