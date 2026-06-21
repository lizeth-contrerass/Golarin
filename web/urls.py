from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('datasets/', views.datasets, name='datasets'),
    path('nuevoParlay/', views.nuevoParlay, name='nuevoParlay'),
    path('logOut/', views.logOut, name='logOut'),
]