from django.shortcuts import render

def inicio(request):
    return render(request, 'web/inicio.html')

def acerca(request):
    return render(request, 'web/acerca.html')
