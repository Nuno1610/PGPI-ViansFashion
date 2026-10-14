from django.template import loader
from django.http import HttpResponse
from django.shortcuts import render
from .models import Escaparate, Articulo
from django.db.models import Q

# Create your views here.
def index(request):
    plantilla = loader.get_template('index.html')
    return HttpResponse(plantilla.render(None, request))

def sobre_nosotros(request):
    return render(request, 'sobre_nosotros.html')

def contacto(request):
    return render(request, 'contacto.html')

def barra_busqueda(request):
    nombre = request.GET.get('nombre', '').strip()
    if nombre:
        productos = productos.filter(Q(nombre__icontains=nombre) | Q(descripcion__icontains=nombre))