from django import forms
from django.contrib.auth.forms import UserCreationForm
from usuarios.models import Usuario
from datetime import date

class FormularioRegistro(UserCreationForm):
    first_name = forms.CharField(max_length=100, required=True, label="Nombre(s)")
    last_name = forms.CharField(max_length=100, required=True, label="Apellido(s)")
    email = forms.EmailField(required=True, label="Correo Electrónico")
    f_nacimiento = forms.DateField(
        required=True,
        label="Fecha de Nacimiento",
        widget=forms.DateInput(attrs={'type': 'date', 'id': 'f_nacimiento'}) # Le asignamos un ID para JS
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("username", "first_name", "last_name", "email", "f_nacimiento")

    # Validación estricta en el Backend
    def clean_f_nacimiento(self):
        f_nacimiento = self.cleaned_data.get('f_nacimiento')
        if f_nacimiento:
            hoy = date.today()
            # Calcular edad exacta considerando año, mes y día
            edad = hoy.year - f_nacimiento.year - ((hoy.month, hoy.day) < (f_nacimiento.month, f_nacimiento.day))
            if edad < 18:
                raise forms.ValidationError("Debes ser mayor de 18 años para registrarte en Golarín.")
        return f_nacimiento