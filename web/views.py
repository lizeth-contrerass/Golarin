from django.shortcuts import render

def inicio(request):
    return render(request, 'web/inicio.html')

def nuevoParlay(request):
    return render(request, 'web/nuevoParlay.html')

def datasets(request):
    return render(request, 'web/datasets.html')

def logOut(request):
    return render(request, 'web/logOut.html')
