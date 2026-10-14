from django.db import models

from django.db import models
from productos.models import Producto, TallaProducto, PersonalizacionUsuario

class Carrito(models.Model):
    cliente = models.OneToOneField('usuarios.Cliente', on_delete=models.CASCADE, related_name='carrito', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Carrito de {self.cliente.usuario or 'Usuario anónimo'}"


class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    talla = models.ForeignKey(TallaProducto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    personalizacion = models.ForeignKey(PersonalizacionUsuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="items_en_carrito"
)

    def __str__(self):
        return f"{self.producto.nombre} ({self.talla.talla}) x {self.cantidad}"

    def subtotal(self):
        return self.cantidad * (self.producto.precio)
