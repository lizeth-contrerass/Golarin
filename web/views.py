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
    ruta_csv_inicial = os.path.join(settings.MEDIA_ROOT, 'datasets_csv', 'partidos_inicial.csv')

    # 1. Obtener todos los datasets cargados por el usuario actual desde el ORM
    datasets_usuario = Dataset.objects.filter(usuario=request.user).order_by('-fecha_subida')

    # 2. Identificar qué dataset se quiere visualizar
    # Puede venir de un cambio en el selector (?id_dataset=...) o tras subir uno nuevo
    id_dataset_seleccionado = request.GET.get('id_dataset')

    columnas = []
    partidos = []
    nombre_dataset_actual = "Dataset Inicial Predeterminado"
    ruta_csv_actual = ruta_csv_inicial

    # Procesar la subida de un nuevo archivo CSV
    if request.method == 'POST' and request.FILES.get('archivo_csv'):
        archivo = request.FILES['archivo_csv']

        if not archivo.name.endswith('.csv'):
            messages.error(request, "El archivo debe tener formato .csv")
            return redirect('datasets')

        nuevo_dataset = Dataset.objects.create(
            usuario=request.user,
            nombre_archivo=archivo.name,
            archivo=archivo
        )
        messages.success(request, f"¡Archivo '{archivo.name}' cargado exitosamente!")

        # Al subir uno nuevo, lo dejamos como el activo inmediatamente
        ruta_csv_actual = nuevo_dataset.archivo.path
        nombre_dataset_actual = nuevo_dataset.nombre_archivo
        id_dataset_seleccionado = str(nuevo_dataset.id)

    elif id_dataset_seleccionado and id_dataset_seleccionado != 'base':
        # Si el usuario seleccionó un dataset propio en el menú desplegable
        try:
            dataset_obj = Dataset.objects.get(id=id_dataset_seleccionado, usuario=request.user)
            ruta_csv_actual = dataset_obj.archivo.path
            nombre_dataset_actual = dataset_obj.nombre_archivo
        except Dataset.DoesNotExist:
            messages.error(request, "El dataset seleccionado no existe o no tienes permiso.")
            ruta_csv_actual = ruta_csv_inicial

    # 3. Intentar leer el CSV seleccionado con Pandas
    if os.path.exists(ruta_csv_actual):
        try:
            df = pd.read_csv(ruta_csv_actual)
            if df.empty:
                messages.warning(request, "El archivo CSV seleccionado está vacío.")
            else:
                columnas = df.columns.tolist()
                partidos = df.head(10).values.tolist()
        except Exception as e:
            messages.error(request, f"Error al procesar el archivo CSV: {str(e)}")

    contexto = {
        'columnas': columnas,
        'partidos': partidos,
        'nombre_dataset': nombre_dataset_actual,
        'datasets_usuario': datasets_usuario,
        'id_seleccionado': id_dataset_seleccionado or 'base'
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
            # Guarda de forma segura en la base de datos (encriptando la contraseña)
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
        # AuthenticationForm ya viene integrado en Django y valida usuario y contraseña
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # Autentica las credenciales contra la Base de Datos
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)  # Crea la sesión del usuario en el servidor
                messages.success(request, f"¡Hola de nuevo, {user.username}!")
                return redirect('inicio')  # <-- Redirección al inicio exitoso
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


# SESIÓN REQUERIDA PARA EL PANEL DE INICIO (SIDEBAR)
@login_required(login_url='login')
def inicio(request):
    # Aquí puedes enviar datos específicos si el usuario es administrador
    es_admin = request.user.is_staff or request.user.is_superuser
    return render(request, 'web/inicio.html', {'es_admin': es_admin})