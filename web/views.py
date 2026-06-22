from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import FormularioRegistro

def nuevoParlay(request):
    return render(request, 'web/nuevoParlay.html')

def datasets(request):
    return render(request, 'web/datasets.html')

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
            messages.success(request, f"¡Bienvenido a Golarín, {user.nombre}!")
            return redirect('inicio')
    else:
        form = FormularioRegistro()
    return render(request, 'web/registro.html', {'form': form})


def login_vista(request):
    if request.user.is_authenticated:
        return redirect('inicio')

    if request.method == 'POST':
        usuario = request.POST.get('username')
        clave = request.POST.get('password')

        # Validación limpia contra inyecciones y ataques
        user = authenticate(request, username=usuario, password=clave)
        if user is not None:
            if user.estado:  # Validamos tu columna 'estado' (si está activo)
                login(request, user)
                return redirect('inicio')
            else:
                messages.error(request, "Esta cuenta se encuentra deshabilitada.")
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, 'web/logIn.html')


def logout_vista(request):
    logout(request)
    return redirect('index')


# SESIÓN REQUERIDA PARA EL PANEL DE INICIO (SIDEBAR)
@login_required(login_url='logIn')
def inicio(request):
    # Aquí puedes enviar datos específicos si el usuario es administrador
    es_admin = request.user.is_staff or request.user.is_superuser
    return render(request, 'web/inicio.html', {'es_admin': es_admin})