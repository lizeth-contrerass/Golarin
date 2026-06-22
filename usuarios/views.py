from rest_framework import generics

from .serializers import RegistroSerializer


class RegistroView(generics.CreateAPIView):

    serializer_class = RegistroSerializer