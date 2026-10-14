from productos.models import Producto, TallaProducto, ImagenProducto, Marca, Categoria
from home.models import Articulo, Escaparate
from pedidos.models import Pedido, ItemPedido
from cesta.models import Carrito, ItemCarrito
from usuarios.models import Cliente
from django.contrib.auth.models import User

def run():

    User.objects.filter(username__startswith="test_").delete()
    Producto.objects.filter(nombre__startswith="TEST_").delete()
    Categoria.objects.filter(nombre__startswith="TEST_").delete()
    Marca.objects.filter(nombre__startswith="TEST_").delete()
    Articulo.objects.filter(nombre__startswith="TEST_").delete()
    Pedido.objects.filter(numero_pedido__startswith="TEST_").delete()

print("Datos de prueba eliminados correctamente.")
