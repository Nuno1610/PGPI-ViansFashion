from django.shortcuts import render

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import LoginClienteForm, RegistroClienteForm
from usuarios.models import Cliente

def registro_cliente(request):
    if request.method == 'POST':
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tu cuenta ha sido creada con éxito. ¡Bienvenido a Vians Fashion!')
            return redirect('iniciar_sesion')  # redirige al login después del registro
    else:
        form = RegistroClienteForm()
    return render(request, 'usuarios/registro_cliente.html', {'form': form})

def iniciar_sesion(request):
    if request.method == 'POST':
        form = LoginClienteForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            # Obtener usuario por el email
            try:
                user = User.objects.get(email=email)
                # Autenticamos con el username del usuario encontrado
                user = authenticate(request, username=user.username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('home') # redirige a home
                else:
                    messages.error(request, 'Correo electrónico o contraseña incorrectos.')
            except User.DoesNotExist:
                messages.error(request, 'No existe una cuenta con ese correo electrónico.')
            return redirect('iniciar_sesion')

    else:
        form = LoginClienteForm()

    return render(request, 'usuarios/login.html', {'form': form})

def cerrar_sesion(request):
    logout(request)
    messages.info(request, "Has cerrado sesión exitosamente.")
    return redirect("home") # redirige a home


# Decorador para permitir solo a superusuarios
def admin_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)

@admin_required
def listar_clientes(request):
    clientes = Cliente.objects.select_related('usuario').all()
    return render(request, 'usuarios/gestor_clientes.html', {'clientes': clientes})

@admin_required
def eliminar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    user = cliente.usuario
    user.delete()  # Esto elimina también el Cliente por relación OneToOne
    messages.success(request, f"Cliente {user.username} eliminado correctamente.")
    return redirect('gestor_clientes')