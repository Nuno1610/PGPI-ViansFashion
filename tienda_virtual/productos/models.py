from django.db import models
from django.utils.text import slugify

class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    imagen = models.ImageField(upload_to='marcas/', blank=True, null=True)

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to='categorias/', blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True) # Slug del nombre para las urls

    def save(self, *args, **kwargs):
        if not self.slug:  
            self.slug = slugify(self.nombre) 
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    GENERO_CHOICES = [
        ('H', 'Hombre'),
        ('M', 'Mujer'),
        ('U', 'Unisex'),
        ('K', 'Kids'),
    ]

    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True, related_name='productos')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='productos')
    genero = models.CharField(max_length=1, choices=GENERO_CHOICES, default='U')
    color = models.CharField(max_length=50, blank=True)
    material = models.CharField(max_length=100, blank=True)
    es_destacado = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    es_visible = models.BooleanField(default=True)


    def __str__(self):
        return self.nombre
    
    @property
    def stock_total(self):
        """Suma del stock de todas las tallas."""
        return sum(talla.stock for talla in self.tallas.all())

    @property
    def esta_disponible(self):
        """Disponible si alguna talla tiene stock > 0."""
        return self.stock_total > 0
    
    @property
    def imagen_principal(self):
        img = self.imagenes.filter(es_principal=True).first()
        if img:
            return img.imagen
        return None
    
    @property
    def es_personalizable(self):
        return hasattr(self, "productopersonalizable")

class ImagenProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='productos/')
    es_principal = models.BooleanField(default=False)
    color = models.CharField(max_length=50, blank=False, null=False, default="default")

    def __str__(self):
        return f"Imagen de {self.producto.nombre} ({'principal' if self.es_principal else 'secundaria'})"


class TallaProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='tallas')
    talla = models.CharField(max_length=30)  # p.ej 'S', 'M', 'L', '42', etc.
    stock = models.IntegerField(default=0)

    class Meta:
        unique_together = ('producto', 'talla')

    def __str__(self):
        return f"{self.producto.nombre} - {self.talla}"

class ProductoPersonalizable(Producto):
    class Meta:
        verbose_name = "Producto personalizable"
        verbose_name_plural = "Productos personalizables"

class PersonalizacionUsuario(models.Model):
    usuario = models.ForeignKey("auth.User", on_delete=models.CASCADE, null=True, blank=True)
    producto_base = models.ForeignKey(ProductoPersonalizable, on_delete=models.CASCADE, related_name="personalizaciones")

    texto = models.CharField(max_length=50, blank=True)
    imagen_subida = models.ImageField(upload_to="personalizaciones/", blank=True, null=True)

    # La imagen generada (el preview final)
    imagen_generada = models.ImageField(upload_to="personalizaciones/final/", blank=True, null=True)

    fecha = models.DateTimeField(auto_now_add=True)

    cantidad = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Personalización de {self.producto_base.nombre} ({self.usuario})"