import os
import pandas as pd
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .forms import FormularioRegistro
from .models import Dataset


@login_required(login_url='login')
def nuevoParlay(request):
    return render(request, 'web/nuevoParlay.html')


@login_required(login_url='login')
def datasets(request):
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

        # Guardar en base de datos.
        Dataset.objects.create(
            usuario=request.user,
            nombre_archivo=archivo.name,
            algoritmo=algoritmo,
            archivo=archivo
        )
        messages.success(request, f"¡Archivo '{archivo.name}' cargado para {algoritmo} exitosamente!")
        return redirect('datasets')

    # 2. MANEJO DE VISUALIZACIÓN Y FILTROS (GET)
    id_dataset_seleccionado = request.GET.get('id_dataset')
    tipo_vista = request.GET.get('tipo') # 'propio' o 'predeterminado'
    filtro_algo = request.GET.get('algo', 'TODOS') # KNN, NB o TODOS

    # -- Datasets Propios (De la BD) --
    datasets_usuario = Dataset.objects.filter(usuario=request.user).order_by('-fecha_subida')
    if filtro_algo != 'TODOS':
        datasets_usuario = datasets_usuario.filter(algoritmo=filtro_algo)

    # -- Datasets Predeterminados (Lectura local de las carpetas) --
    datasets_predeterminados = []
    ruta_base = os.path.join(settings.MEDIA_ROOT, 'datasets_csv')

    # Buscar en carpeta KNN
    if filtro_algo in ['TODOS', 'KNN']:
        knn_dir = os.path.join(ruta_base, 'knn')
        if os.path.exists(knn_dir):
            for f in os.listdir(knn_dir):
                if f.endswith('.csv'):
                    datasets_predeterminados.append({'id': f'knn_{f}', 'nombre': f, 'algo': 'KNN', 'ruta': os.path.join(knn_dir, f)})

    # Buscar en carpeta Naive Bayes
    if filtro_algo in ['TODOS', 'NB']:
        nb_dir = os.path.join(ruta_base, 'naivebayes')
        if os.path.exists(nb_dir):
            for f in os.listdir(nb_dir):
                if f.endswith('.csv'):
                    datasets_predeterminados.append({'id': f'nb_{f}', 'nombre': f, 'algo': 'NB', 'ruta': os.path.join(nb_dir, f)})

    columnas = []
    partidos = []
    nombre_dataset_actual = "Ninguno seleccionado"
    ruta_csv_actual = None

    # 3. DETERMINAR QUÉ ARCHIVO LEER CON PANDAS
    if id_dataset_seleccionado:
        if tipo_vista == 'propio':
            try:
                dataset_obj = Dataset.objects.get(id=id_dataset_seleccionado, usuario=request.user)
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

    # 4. LEER CSV SELECCIONADO
    if ruta_csv_actual and os.path.exists(ruta_csv_actual):
        try:
            df = pd.read_csv(ruta_csv_actual)
            if df.empty:
                messages.warning(request, "El archivo CSV está vacío.")
            else:
                columnas = df.columns.tolist()
                partidos = df.head(10).values.tolist()
        except Exception as e:
            messages.error(request, f"Error al leer el archivo: {str(e)}")

    contexto = {
        'columnas': columnas,
        'partidos': partidos,
        'nombre_dataset': nombre_dataset_actual,
        'datasets_usuario': datasets_usuario,
        'datasets_predeterminados': datasets_predeterminados,
        'id_seleccionado': id_dataset_seleccionado,
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
            # Guarda de forma segura en la base de datos
            user = form.save()
            # Inicia la sesión automáticamente tras el registro exitoso
            login(request, user)
            messages.success(request, f"¡Bienvenido a Golarín, {user.first_name}!")
            return redirect('inicio')
    else:
        form = FormularioRegistro()
    return render(request, 'web/registro.html', {'form': form})


def login_vista(request):
    # Si el usuario ya inició sesión, lo mandamos directo al inicio
    if request.user.is_authenticated:
        return redirect('inicio')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # Autentica las credenciales
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