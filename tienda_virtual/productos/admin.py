from django.contrib import admin
from .models import Producto, Marca, Categoria, ImagenProducto, TallaProducto

admin.site.register(Marca)
admin.site.register(Categoria)
admin.site.register(Producto)
admin.site.register(ImagenProducto)
admin.site.register(TallaProducto)
