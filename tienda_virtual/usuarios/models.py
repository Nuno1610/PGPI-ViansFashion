from django.db import models
from django.contrib.auth.models import User

class Cliente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=20)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.usuario.first_name} {self.usuario.last_name}"