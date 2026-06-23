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


@login_required(login_url='login')
def nuevoParlay(request):
    return render(request, 'web/nuevoParlay.html')


@login_required(login_url='login')
def datasets(request):
    dataset_actual = None
    # 1. PROCESAR SUBIDA DE ARCHIVO (POST)
    if request.method == 'POST' and request.FILES.get('archivo_csv'):
        archivo = request.FILES['archivo_csv']
        algoritmo = request.POST.get('algoritmo_destino')

        if not archivo.name.endswith('.csv'):
            messages.error(request, "El archivo debe tener formato .csv")
            return redirect('datasets')

        if algoritmo not in ['KNN', 'NB']:
            messages.error(request, "Selecciona un algoritmo válido.")
            return redirect('datasets')

        # Se crea la instancia inicial para guardar el archivo físicamente en el disco
        obj = Dataset.objects.create(
            usuario=request.user,
            nombre_archivo=archivo.name,
            algoritmo=algoritmo,
            archivo=archivo
        )

        try:
            # Lectura del archivo recién guardado con pandas
            df = pd.read_csv(obj.archivo.path)

            if df.empty:
                obj.delete()
                messages.error(request, "El archivo CSV está vacío.")
                return redirect('datasets')

            # Estructura base supuesta: [ID, características..., Clase]
            cols_caracteristicas = df.columns[1:-1].tolist()
            col_clases = df.columns[-1]
            clases = [str(c) for c in df[col_clases].unique()]

            cols_discretas = []
            cols_continuas = []
            valores_caracteristicas = {}

            # Clasificar dinámicamente columnas discretas y continuas
            for cat in cols_caracteristicas:
                primer_valor = df[cat].dropna().iloc[0] if not df[cat].dropna().empty else "Texto"
                if not es_continuo(primer_valor):
                    cols_discretas.append(cat)
                    valores_caracteristicas[cat] = [str(v).capitalize() for v in df[cat].unique()]
                else:
                    cols_continuas.append(cat)

            # Poblar metadatos estructurales en el modelo
            obj.col_clases = col_clases
            obj.clases = clases
            obj.cols_caracteristicas = cols_caracteristicas
            obj.cols_discretas = cols_discretas
            obj.cols_continuas = cols_continuas
            obj.valores_caracteristicas = valores_caracteristicas

            # --- PROCESAMIENTO SEGÚN EL ALGORITMO ---
            if algoritmo == 'NB':
                # Cálculos probabilísticos de Naive Bayes
                prob_clases = nb_prob_clases(df, col_clases, clases)
                prob_cond = nb_prob_cond_discreta(df, cols_discretas, col_clases, clases)
                param_cont = nb_parametros_continuos(df, cols_continuas, col_clases, clases)

                # Persistencia en campos JSON
                obj.nb_probabilidades_clases = prob_clases
                obj.nb_probabilidades_condicionales = prob_cond
                obj.nb_parametros_cont = param_cont

                # Evaluación por resustitución
                acc, err, prec, rec, esp = verificar_naive_bayes(
                    df, cols_caracteristicas, col_clases, clases,
                    prob_clases, prob_cond, param_cont, cols_discretas, cols_continuas
                )

            # Asignación de métricas globales de rendimiento
            obj.accuracy = acc
            obj.error = err
            obj.precision = prec
            obj.recall = rec
            obj.especificidad = esp
            obj.procesado = True
            obj.save()

            messages.success(request, f"¡Archivo '{archivo.name}' cargado, procesado y evaluado con éxito!")

        except Exception as e:
            print("=========================================")
            print(f"ERROR CRÍTICO AL PROCESAR EL DATASET: {str(e)}")
            import traceback
            traceback.print_exc()  # Esto te dirá la línea exacta del error
            print("=========================================")
            # Reversión y limpieza física en caso de fallo matemático
            if obj.id:
                if obj.archivo and os.path.exists(obj.archivo.path):
                    os.remove(obj.archivo.path)
                obj.delete()
            messages.error(request, f"Error al procesar la estructura del dataset: {str(e)}")

        return redirect('datasets')

    # 2. MANEJO DE VISUALIZACIÓN Y FILTROS (GET)
    id_dataset_seleccionado = request.GET.get('id_dataset')
    tipo_vista = request.GET.get('tipo')
    filtro_algo = request.GET.get('algo', 'TODOS')

    # -- Datasets Propios --
    datasets_usuario = Dataset.objects.filter(usuario=request.user).order_by('-fecha_subida')
    if filtro_algo != 'TODOS':
        datasets_usuario = datasets_usuario.filter(algoritmo=filtro_algo)

    # -- Datasets Predeterminados --
    datasets_predeterminados = []
    ruta_base = os.path.join(settings.MEDIA_ROOT, 'datasets_csv')

    if filtro_algo in ['TODOS', 'NB']:
        nb_dir = os.path.join(ruta_base, 'naivebayes')
        if os.path.exists(nb_dir):
            for f in os.listdir(nb_dir):
                if f.endswith('.csv'):
                    datasets_predeterminados.append(
                        {'id': f'nb_{f}', 'nombre': f, 'algo': 'NB', 'ruta': os.path.join(nb_dir, f)})

    columnas = []
    partidos = []
    nombre_dataset_actual = "Ninguno seleccionado"
    ruta_csv_actual = None

    # 3. DETERMINAR QUÉ ARCHIVO LEER CON PANDAS
    if id_dataset_seleccionado:
        if tipo_vista == 'propio':
            try:
                dataset_obj = Dataset.objects.get(id=id_dataset_seleccionado, usuario=request.user)
                dataset_actual = dataset_obj  # <-- 2. ASIGNA EL OBJETIVO ENCONTRADO
                ruta_csv_actual = dataset_obj.archivo.path
                nombre_dataset_actual = f"{dataset_obj.nombre_archivo} ({dataset_obj.get_algoritmo_display()})"
            except Dataset.DoesNotExist:
                messages.error(request, "Dataset propio no encontrado.")

        elif tipo_vista == 'predeterminado':
            for ds in datasets_predeterminados:
                if ds['id'] == id_dataset_seleccionado:
                    ruta_csv_actual = ds['ruta']
                    nombre_dataset_actual = f"{ds['nombre']} ({ds['algo']})"
                    break
            if not ruta_csv_actual:
                messages.error(request, "Dataset predeterminado no encontrado.")

    # 4. LEER CSV SELECCIONADO PARA PASARSE A LA TABLA HTML
    if ruta_csv_actual and os.path.exists(ruta_csv_actual):
        try:
            df_view = pd.read_csv(ruta_csv_actual)
            if df_view.empty:
                messages.warning(request, "El archivo CSV está vacío.")
            else:
                columnas = df_view.columns.tolist()
                partidos = df_view.head(10).values.tolist()
        except Exception as e:
            messages.error(request, f"Error al leer el archivo: {str(e)}")

    contexto = {
        'columnas': columnas,
        'partidos': partidos,
        'nombre_dataset': nombre_dataset_actual,
        'datasets_usuario': datasets_usuario,
        'datasets_predeterminados': datasets_predeterminados,
        'id_seleccionado': id_dataset_seleccionado,
        'dataset_actual': dataset_actual,
    }

    return render(request, 'web/datasets.html', contexto)


def historial(request):
    return render(request, 'web/historial.html')


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
    es_admin = request.user.is_staff or request.user.is_superuser
    return render(request, 'web/inicio.html', {'es_admin': es_admin})


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