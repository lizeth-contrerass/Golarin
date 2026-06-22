from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Ruta para el panel de administración de Django (opcional, pero recomendada)
    path('admin/', admin.site.urls),

    # Conecta la raíz del proyecto con las rutas de tu aplicación "web"
    path('', include('web.urls')),

    # Conecta la ruta api/usuarios/ con tu aplicación "usuarios"
    path('api/usuarios/', include('usuarios.urls')),
]