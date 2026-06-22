from django.urls import path

from .views import RegistroView

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
)

urlpatterns = [

    path(
        'registro/',
        RegistroView.as_view()
    ),

    path(
        'login/',
        TokenObtainPairView.as_view()
    ),

    path(
        'refresh/',
        TokenRefreshView.as_view()
    )
]