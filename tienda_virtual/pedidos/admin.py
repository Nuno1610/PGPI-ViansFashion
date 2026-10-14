from django.contrib import admin

from django.contrib import admin
from .models import Pedido, ItemPedido

admin.site.register(Pedido)
admin.site.register(ItemPedido)