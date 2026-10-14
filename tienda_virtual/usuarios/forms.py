from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Cliente

# Formulario registro
class RegistroClienteForm(UserCreationForm):
    direccion = forms.CharField(max_length=255, required=True, label="Dirección")
    ciudad = forms.CharField(max_length=100, required=True, label="Ciudad")
    telefono = forms.RegexField(
        regex=r'^\d+$',
        max_length=20,
        required=True,
        label="Teléfono",
        error_messages={"invalid": "Solo se permiten números."},
        widget=forms.TextInput(attrs={
            'inputmode': 'numeric',
            'pattern': '[0-9]*'
        })
    )

    codigo_postal = forms.RegexField(
        regex=r'^\d+$',
        max_length=10,
        required=True,
        label="Código postal",
        error_messages={"invalid": "Solo se permiten números."},
        widget=forms.TextInput(attrs={
            'inputmode': 'numeric',
            'pattern': '[0-9]*'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control bg-dark text-light', 'placeholder': 'Nombre de usuario'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control bg-dark text-light', 'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control bg-dark text-light', 'placeholder': 'Apellidos'}),
            'email': forms.EmailInput(attrs={'class': 'form-control bg-dark text-light', 'placeholder': 'Correo electrónico'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Añadir estilos a todos los campos
        for name, field in self.fields.items():
            classes = field.widget.attrs.get('class', '')
            field.widget.attrs.update({
                'class': f'{classes} form-control bg-dark text-light'.strip(),
                'placeholder': field.label
            })

    def save(self, commit=True):
        usuario = super().save(commit=commit)
        if commit:
            Cliente.objects.create(
                usuario=usuario,
                telefono=self.cleaned_data['telefono'],
                direccion=self.cleaned_data['direccion'],
                ciudad=self.cleaned_data['ciudad'],
                codigo_postal=self.cleaned_data['codigo_postal']
            )
        return usuario


# Formulario Login
class LoginClienteForm(forms.Form):
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'class': 'form-control bg-dark text-light', 'placeholder': 'Correo electrónico'})
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control bg-dark text-light', 'placeholder': 'Contraseña'})
    )

