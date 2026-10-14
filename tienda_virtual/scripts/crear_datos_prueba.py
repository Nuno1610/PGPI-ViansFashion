from django.contrib.auth.models import User
from productos.models import Marca, Categoria, Producto, TallaProducto, ImagenProducto, ProductoPersonalizable
from pedidos.models import Pedido, ItemPedido
from cesta.models import Carrito, ItemCarrito
from usuarios.models import Cliente
from home.models import Articulo, Escaparate
from django.core.files import File
from decimal import Decimal
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # apunta a la raíz del proyecto

def run():

    # Clientes de prueba
    clientes = []
    for i in range(1, 4):
        username = f"test_cliente{i}"  # prefijo test para borrar
        user, created = User.objects.get_or_create(username=username)
        if created:
            user.first_name = f"Nombre{i}"
            user.last_name = f"Apellido{i}"
            user.email = f"{username}@example.com"
            user.set_password("12345678!Aa") 
            user.save()

        cliente, _ = Cliente.objects.get_or_create(
            usuario=user,
            defaults={
                "telefono": f"6000000{i}",
                "direccion": f"Calle Falsa {i}",
                "ciudad": "Sevilla",
                "codigo_postal": f"4100{i}"
            }
        )
        clientes.append(cliente)

    # Marcas de prueba
    marcas = []
    for name in ["TEST_Marca1", "TEST_Marca2", "TEST_Marca3"]:
        marca, _ = Marca.objects.get_or_create(nombre=name)
        marcas.append(marca)

    # Categorias de prueba
    categorias = []
    for name in ["TEST_Gorras", "TEST_Sudaderas", "TEST_Camisetas"]:
        cat, _ = Categoria.objects.get_or_create(nombre=name, descripcion=f"Categoria de {name}")
        categorias.append(cat)

    # Productos de prueba
    productos = []
    for i in range(1, 6):
        producto, _ = Producto.objects.get_or_create(
            nombre=f"TEST_Producto {i}",
            defaults={
                "descripcion": f"Descripcion del producto {i}",
                "precio": Decimal(random.randint(10, 100)),
                "marca": random.choice(marcas),
                "categoria": random.choice(categorias),
                "genero": random.choice(['H','M','U']),
                "color": random.choice(['Rojo','Azul','Negro']),
                "material": random.choice(['Algodon','Cuero','Sintético']),
                "es_destacado": random.choice([True, False])
            }
        )
        productos.append(producto)

        # Tallas
        for talla_name in ['S','M','L','XL']:
            TallaProducto.objects.get_or_create(
                producto=producto,
                talla=talla_name,
                defaults={"stock": random.randint(0,20)}
            )

        # Imagenes
        media_productos_dir = BASE_DIR / "media" / "productos"
        img_defaut_dir = media_productos_dir / "default.png"
        if img_defaut_dir.exists():
            ImagenProducto.objects.get_or_create(
                producto=producto,
                imagen=f"productos/{img_defaut_dir.name}",
                es_principal=True
            )
        else:
            print(f"¡Aviso! Imagen por defecto no encontrada en {img_defaut_dir}")
    
    # Productos PERSONALIZABLES de prueba
    productos_personalizables = []

    # Lista de imágenes base
    imagenes_base = [
        ["camiseta_blanca.png", "camiseta_negra.png"],
        ["larga_blanca.png", "larga_negra.png"],
        ["gorra_blanca.png", "gorra_negra.png"],
        ["sudadera_blanca.png", "sudadera_negra.png"]
    ]

    for idx, lista_imagenes in enumerate(imagenes_base, start=1):

        producto_base, created = ProductoPersonalizable.objects.get_or_create(
            nombre=f"TEST_Personalizable {idx}",
            defaults={
                "descripcion": "Producto personalizable de prueba",
                "precio": Decimal(random.randint(15, 60)),
                "marca": random.choice(marcas),
                "categoria": random.choice(categorias),
                "genero": random.choice(['H','M','U']),
                "color": "Blanco",
                "material": "Algodón",
                "es_destacado": True,
            }
        )

        for i, name in enumerate(lista_imagenes):
            if "blanca" in name:
                color = "Blanco"
            elif "negra" in name:
                color = "Negro"
            else:
                color = producto_base.color  # default
            # Crear ImagenProducto principal vinculada al producto
            ImagenProducto.objects.get_or_create(
                producto=producto_base,
                imagen=f"productos/{name}",
                es_principal= (i == 0),
                color= color
            )

        productos_personalizables.append(producto_base)

        # Tallas
        for talla_name in ['S','M','L','XL']:
            TallaProducto.objects.get_or_create(
                producto=producto_base,
                talla=talla_name,
                defaults={"stock": random.randint(5, 30)}
            )
    # Articulos y Escaparate
    articulos = []
    for i in range(1,4):
        art, _ = Articulo.objects.get_or_create(
            nombre=f"TEST_Articulo {i}",
            defaults={"descripcion": f"Descripcion del articulo {i}"}
        )
        articulos.append(art)
        Escaparate.objects.get_or_create(articulo=art)

    # Carritos
    for cliente in clientes:
        carrito, _ = Carrito.objects.get_or_create(cliente=cliente)
        for producto in random.sample(productos, 2):
            talla = producto.tallas.first()
            ItemCarrito.objects.get_or_create(
                carrito=carrito,
                producto=producto,
                talla=talla,
                defaults={"cantidad": random.randint(1,3)}
            )

    # Pedidos
    for cliente in clientes:
        pedido, _ = Pedido.objects.get_or_create(
            cliente=cliente,
            numero_pedido=f"TEST_PED{random.randint(1000,9999)}",
            defaults={
                "nombre_cliente": f"{cliente.usuario.first_name} {cliente.usuario.last_name}",
                "email": cliente.usuario.email,
                "metodo_pago": "Tarjeta",
                "stripe_payment_intent": f"pi_{random.randint(1000000,9999999)}",
                "pago_completado": random.choice([True, False]),
                "direccion_envio": cliente.direccion,
                "telefono": cliente.telefono,
                "impuestos": Decimal("5.00"),
                "coste_entrega": Decimal("3.00"),
                "descuento": Decimal("2.00"),
                "estado": "PROC"
            }
        )

        for producto in random.sample(productos, 2):
            talla = producto.tallas.first()
            cantidad = random.randint(1,3)
            precio = producto.precio
            ItemPedido.objects.get_or_create(
                pedido=pedido,
                producto=producto,
                talla=talla.talla,
                cantidad=cantidad,
                precio_unitario=precio,
                total=precio * cantidad
            )

    print("Datos de prueba creados correctamente.")
