from django.urls import path
from . import views

urlpatterns = [
    path('', views.render, {'template_name': 'web/index.html'}, name='index'),
    path('registro/', views.registro_vista, name='registro'),
    path('login/', views.login_vista, name='login'),
    path('logout/', views.logout_vista, name='logOut'),
    path('inicio/', views.inicio, name='inicio'),
    path('datasets/', views.datasets, name='datasets'),
    path('nuevoParlay/', views.nuevoParlay, name='nuevoParlay'),
]