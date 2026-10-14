from django.db import models
from django import forms
from usuarios.models import Cliente
from productos.models import Producto, PersonalizacionUsuario

class Pedido(models.Model):
    ESTADOS = [
        ('PEND', 'Pendiente'), # Se usa en el proceso de checkout, cuando no se ha pagado todavia
        ('ENRV', 'En revisión'),
        ('PROC', 'En proceso'),
        ('ENVI', 'Enviado'),
        ('ENTR', 'Entregado'),
        ('CANC', 'Cancelado'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, related_name='pedidos', null=True, blank=True) # Puede no estar registrado como cliente
    nombre_cliente = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    numero_pedido = models.CharField(max_length=20, unique=True)
    estado = models.CharField(max_length=4, choices=ESTADOS, default='ENRV')
    impuestos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coste_entrega = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    metodo_pago = models.CharField(max_length=50)
    direccion_envio = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20)
    stripe_payment_intent = models.CharField(max_length=100, blank=True, null=True)  # ID de Stripe
    pago_completado = models.BooleanField(default=False)  # Indica si el pago fue exitoso

    def __str__(self):
        return f"Pedido {self.numero_pedido} - {self.cliente}"

    @property
    def subtotal(self):
        """Suma de los totales de los ítems."""
        return sum(item.total for item in self.items.all())

    @property
    def total(self):
        """Subtotal + impuestos + envío - descuentos."""
        return self.subtotal + self.impuestos + self.coste_entrega - self.descuento

class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    talla = models.CharField(max_length=30, blank=True)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    personalizacion = models.ForeignKey(
        PersonalizacionUsuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items"
    )

    def save(self, *args, **kwargs):
        self.total = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.producto} ({self.talla})"