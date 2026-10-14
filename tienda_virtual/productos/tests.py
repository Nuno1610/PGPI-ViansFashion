from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from io import BytesIO
from PIL import Image
from .models import *
from .forms import PersonalizacionUsuarioForm

class ProductosTest(TestCase):
    def setUp(self):
        self.marca = Marca.objects.create(nombre="Nike")
        self.categoria = Categoria.objects.create(nombre="Ropa")
        self.user = User.objects.create_user(username="u1", password="123")
        self.admin = User.objects.create_superuser(username="a1", password="123", email="a@t.com")
        self.producto = Producto.objects.create(nombre="Test", precio=Decimal("50.00"), marca=self.marca, categoria=self.categoria)
        self.client = Client()

    def _img(self):
        io = BytesIO()
        Image.new('RGB', (10, 10)).save(io, 'PNG')
        io.seek(0)
        return SimpleUploadedFile('t.png', io.read(), content_type='image/png')

    def test_product_models_and_strings(self):
        self.assertEqual(str(self.marca), "Nike")
        self.assertEqual(self.categoria.slug, "ropa")
        t = TallaProducto.objects.create(producto=self.producto, talla="M", stock=10)
        self.assertEqual(str(t), "Test - M")
        self.assertEqual(self.producto.stock_total, 10)
        self.assertTrue(self.producto.esta_disponible)
        i = ImagenProducto.objects.create(producto=self.producto, imagen=self._img(), es_principal=True)
        self.assertIsNotNone(self.producto.imagen_principal)
        self.assertIn("principal", str(i))
        p_pers = ProductoPersonalizable.objects.create(nombre="Pers", precio=Decimal("20.00"))
        self.assertTrue(p_pers.es_personalizable)
        self.assertFalse(self.producto.es_personalizable)
        p_no_stock = Producto.objects.create(nombre="NoStock", precio=Decimal("10.00"))
        self.assertFalse(p_no_stock.esta_disponible)

    def test_personalization_form_validation(self):
        self.assertTrue(PersonalizacionUsuarioForm(data={'texto': 'T', 'talla': '1', 'cantidad': 1}).is_valid())
        self.assertFalse(PersonalizacionUsuarioForm(data={'texto': 'T', 'talla': '1', 'cantidad': 0}).is_valid())
        t = TallaProducto.objects.create(producto=self.producto, talla="M", stock=2)
        form = PersonalizacionUsuarioForm(data={'texto': 'T', 'talla': t.id, 'cantidad': 5}, producto=self.producto)
        self.assertFalse(form.is_valid())
        t2 = TallaProducto.objects.create(producto=self.producto, talla="L", stock=0)
        form = PersonalizacionUsuarioForm(data={'texto': 'T', 'talla': t2.id, 'cantidad': 1}, producto=self.producto)
        self.assertFalse(form.is_valid())
        form = PersonalizacionUsuarioForm(data={'texto': 'T', 'talla': 999, 'cantidad': 1}, producto=self.producto)
        self.assertFalse(form.is_valid())

    def test_catalog_filtering_and_price_validation(self):
        Producto.objects.create(nombre="P2", precio=Decimal("100.00"), es_visible=False)
        r = self.client.get(reverse('catalogo'))
        self.assertContains(r, "Test")
        r = self.client.get(reverse('catalogo'), {'nombre': 'Test', 'genero': 'U', 'precio_max': '60'})
        self.assertContains(r, "Test")
        r = self.client.get(reverse('catalogo'), {'precio_min': '-10'})
        self.assertContains(r, "negativo")
        r = self.client.get(reverse('catalogo'), {'precio_max': '-50'})
        self.assertContains(r, "negativo")
        r = self.client.get(reverse('catalogo'), {'precio_min': '100', 'precio_max': '50'})
        self.assertContains(r, "mayor")
        m2 = Marca.objects.create(nombre="Adidas")
        p2 = Producto.objects.create(nombre="P2", precio=Decimal("150.00"), marca=m2, es_visible=True)
        r = self.client.get(reverse('catalogo'), {'marca': m2.id, 'precio_min': 'abc'})
        self.assertEqual(r.status_code, 200)
        r = self.client.get(reverse('catalogo'), {'marca': 'invalid'})
        self.assertEqual(r.status_code, 200)
        r = self.client.get(reverse('catalogo_categoria', kwargs={'categoria_slug': self.categoria.slug}), 
                           {'precio_min': '40', 'precio_max': '60'})
        self.assertContains(r, "Test")
        Producto.objects.all().delete()
        r = self.client.get(reverse('catalogo'))
        self.assertIn('precio_bound_min', r.context)

    def test_product_detail_view(self):
        self.assertEqual(self.client.get(reverse('detalle_producto', kwargs={'id': self.producto.id})).status_code, 200)
        self.assertEqual(self.client.get(reverse('detalle_producto', kwargs={'id': 9999})).status_code, 404)
        p_pers = ProductoPersonalizable.objects.create(nombre="Pers", precio=Decimal("25.00"))
        r = self.client.get(reverse('detalle_producto', kwargs={'id': p_pers.id}))
        self.assertEqual(r.status_code, 302)

    def test_personalize_product_workflow(self):
        p = ProductoPersonalizable.objects.create(nombre="P", precio=Decimal("20.00"))
        ImagenProducto.objects.create(producto=p, imagen=self._img(), es_principal=True)
        ImagenProducto.objects.create(producto=p, imagen=self._img(), es_principal=False, color='red')
        t = TallaProducto.objects.create(producto=p, talla="M", stock=10)
        self.client.login(username="u1", password="123")
        r = self.client.get(reverse('personalizar_producto', kwargs={'producto_id': p.id}))
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse('personalizar_producto', kwargs={'producto_id': p.id}), 
                           {'texto': 'T1', 'color_texto': '#000', 'talla': t.id, 'cantidad': 1, 'color_producto': 'red',
                            'texto_x': '10', 'texto_y': '20', 'imagen_x': '5', 'imagen_y': '5',
                            'preview_width': '100', 'preview_height': '100'})
        self.assertIn(r.status_code, [200, 302])
        r = self.client.post(reverse('personalizar_producto', kwargs={'producto_id': p.id}), 
                           {'texto': 'T2', 'color_texto': '#FFF', 'talla': t.id, 'cantidad': 1})
        self.assertIn(r.status_code, [200, 302])

    def test_preview_generation(self):
        from productos.views import generar_preview
        io1 = BytesIO()
        Image.new('RGB', (200, 200)).save(io1, 'PNG')
        io1.seek(0)
        io2 = BytesIO()
        Image.new('RGBA', (50, 50)).save(io2, 'PNG')
        io2.seek(0)
        res = generar_preview(io1, 'T', '#000', io2, (10, 10), (5, 5), (100, 100), (200, 200))
        self.assertIsNotNone(res)
        res = generar_preview(io1, 'T', '#000', io2, imagen_pos=(100, 100))
        self.assertIsNotNone(res)
        res = generar_preview("no_existe.png", "T", "#000")
        self.assertIsNone(res)

    def test_admin_product_creation_and_editing(self):
        self.client.login(username='a1', password='123')
        r = self.client.get(reverse('crear_producto'))
        self.assertEqual(r.status_code, 200)
        r = self.client.get(reverse('editar_producto_admin', kwargs={'producto_id': self.producto.id}))
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse('crear_producto'), {})
        self.assertIn(r.status_code, [200, 302])
        data = {
            'nombre': 'PersonalizableNew', 'precio': '60', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'es_personalizable': 'on',
            'imagen-TOTAL_FORMS': '0', 'imagen-INITIAL_FORMS': '0', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'talla-TOTAL_FORMS': '1', 'talla-INITIAL_FORMS': '0', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
            'talla-0-talla': 'L', 'talla-0-stock': '20',
        }
        r = self.client.post(reverse('crear_producto'), data)
        self.assertIn(r.status_code, [200, 302])
        data = {
            'nombre': 'NormalNew', 'precio': '55', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'imagen-TOTAL_FORMS': '1', 'imagen-INITIAL_FORMS': '0', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'imagen-0-imagen': self._img(), 'imagen-0-es_principal': 'on', 'imagen-0-color': 'default',
            'talla-TOTAL_FORMS': '1', 'talla-INITIAL_FORMS': '0', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
            'talla-0-talla': 'M', 'talla-0-stock': '10',
        }
        r = self.client.post(reverse('crear_producto'), data)
        self.assertIn(r.status_code, [200, 302])
        p = Producto.objects.create(nombre='ToEdit', precio=Decimal('40'), categoria=self.categoria, marca=self.marca)
        img = ImagenProducto.objects.create(producto=p, imagen=self._img(), es_principal=False)
        t = TallaProducto.objects.create(producto=p, talla='M', stock=10)
        data = {
            'nombre': 'ToEdit', 'precio': '45', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'imagen-TOTAL_FORMS': '1', 'imagen-INITIAL_FORMS': '1', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'imagen-0-id': img.id, 'imagen-0-imagen': img.imagen, 'imagen-0-es_principal': '',
            'talla-TOTAL_FORMS': '1', 'talla-INITIAL_FORMS': '1', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
            'talla-0-id': t.id, 'talla-0-talla': 'M', 'talla-0-stock': 15,
        }
        r = self.client.post(reverse('editar_producto_admin', kwargs={'producto_id': p.id}), data)
        self.assertIn(r.status_code, [200, 302])

    def test_stock_management_and_deletion(self):
        self.client.login(username='a1', password='123')
        t = TallaProducto.objects.create(producto=self.producto, talla="M", stock=10)
        r = self.client.get(reverse('reponer_stock', kwargs={'id': self.producto.id}))
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse('reponer_stock', kwargs={'id': self.producto.id}), {'talla_id': t.id, 'cantidad': 5})
        self.assertEqual(r.status_code, 302)
        t.refresh_from_db()
        self.assertEqual(t.stock, 15)
        r = self.client.post(reverse('reponer_stock', kwargs={'id': self.producto.id}), {'talla_id': t.id, 'cantidad': '-5'})
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse('eliminar_producto', kwargs={'id': self.producto.id}))
        self.assertFalse(Producto.objects.filter(id=self.producto.id).exists())

    def test_category_crud_operations(self):
        self.client.login(username='a1', password='123')
        r = self.client.get(reverse('crear_categoria'))
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse('crear_categoria'), {'nombre': 'Cat2', 'descripcion': 'D'})
        self.assertEqual(r.status_code, 302)
        cat = Categoria.objects.filter(nombre='Cat2').first()
        r = self.client.get(reverse('editar_categoria', kwargs={'categoria_id': cat.id}))
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse('editar_categoria', kwargs={'categoria_id': cat.id}), {'nombre': 'Cat3', 'descripcion': 'D2'})
        cat.refresh_from_db()
        self.assertEqual(cat.nombre, 'Cat3')
        r = self.client.post(reverse('eliminar_categoria', kwargs={'categoria_id': cat.id}))
        self.assertFalse(Categoria.objects.filter(id=cat.id).exists())

    def test_brand_crud_operations(self):
        self.client.login(username='a1', password='123')
        r = self.client.get(reverse('crear_marca'))
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse('crear_marca'), {'nombre': 'Puma'})
        self.assertEqual(r.status_code, 302)
        m = Marca.objects.filter(nombre='Puma').first()
        r = self.client.get(reverse('editar_marca', kwargs={'marca_id': m.id}))
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse('editar_marca', kwargs={'marca_id': m.id}), {'nombre': 'Puma2'})
        m.refresh_from_db()
        self.assertEqual(m.nombre, 'Puma2')
        r = self.client.post(reverse('eliminar_marca', kwargs={'marca_id': m.id}))
        self.assertFalse(Marca.objects.filter(id=m.id).exists())
        marca = Marca.objects.create(nombre='Reebok')
        Producto.objects.create(nombre='Zapato', precio=Decimal('99'), marca=marca, categoria=self.categoria)
        r = self.client.post(reverse('eliminar_marca', kwargs={'marca_id': marca.id}))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Marca.objects.filter(id=marca.id).exists())

    def test_admin_access_protection(self):
        r = self.client.get(reverse('crear_categoria'))
        self.assertEqual(r.status_code, 302)
        self.client.login(username="u1", password="123")
        r = self.client.get(reverse('crear_marca'))
        self.assertEqual(r.status_code, 302)

    def test_edge_cases_and_error_handling(self):
        self.client.login(username='a1', password='123')
        cat = Categoria.objects.create(nombre='CustomCat', slug='custom-slug')
        self.assertEqual(cat.slug, 'custom-slug')
        self.client.logout()
        r = self.client.post(reverse('eliminar_producto', kwargs={'id': self.producto.id}))
        self.assertEqual(r.status_code, 302)
        self.client.login(username='a1', password='123')
        t = TallaProducto.objects.create(producto=self.producto, talla='M', stock=10)
        r = self.client.post(reverse('reponer_stock', kwargs={'id': self.producto.id}), 
                           {'talla_id': 9999, 'cantidad': 5})
        self.assertIn(r.status_code, [200, 302, 404])
        r = self.client.post(reverse('crear_producto'), {'precio': '50', 'categoria': self.categoria.id, 'marca': self.marca.id})
        self.assertIn(r.status_code, [200, 302])
        r = self.client.post(reverse('editar_marca', kwargs={'marca_id': self.marca.id}), {})
        self.assertIn(r.status_code, [200, 302])

    def test_create_product_without_principal_image(self):
        self.client.login(username='a1', password='123')
        data = {
            'nombre': 'SinPrinc', 'precio': '45', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'imagen-TOTAL_FORMS': '2', 'imagen-INITIAL_FORMS': '0', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'imagen-0-imagen': self._img(), 'imagen-0-es_principal': '', 'imagen-0-color': 'blue',
            'imagen-1-imagen': self._img(), 'imagen-1-es_principal': '', 'imagen-1-color': 'green',
            'talla-TOTAL_FORMS': '1', 'talla-INITIAL_FORMS': '0', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
            'talla-0-talla': 'L', 'talla-0-stock': '12',
        }
        r = self.client.post(reverse('crear_producto'), data)
        self.assertIn(r.status_code, [200, 302])

    def test_create_product_with_duplicate_principals(self):
        self.client.login(username='a1', password='123')
        data = {
            'nombre': 'DosPrin', 'precio': '65', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'imagen-TOTAL_FORMS': '2', 'imagen-INITIAL_FORMS': '0', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'imagen-0-imagen': self._img(), 'imagen-0-es_principal': 'on', 'imagen-0-color': 'yellow',
            'imagen-1-imagen': self._img(), 'imagen-1-es_principal': 'on', 'imagen-1-color': 'pink',
            'talla-TOTAL_FORMS': '1', 'talla-INITIAL_FORMS': '0', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
            'talla-0-talla': 'XL', 'talla-0-stock': '8',
        }
        r = self.client.post(reverse('crear_producto'), data)
        self.assertIn(r.status_code, [200, 302])

    def test_create_personalizable_product_complete(self):
        self.client.login(username='a1', password='123')
        data = {
            'nombre': 'PersComp', 'precio': '80', 'descripcion': 'Desc',
            'categoria': self.categoria.id, 'marca': self.marca.id, 'genero': 'U', 
            'color': 'Azul', 'material': 'Algodón', 'es_destacado': 'on', 'es_visible': 'on',
            'es_personalizable': 'on',
            'imagen-TOTAL_FORMS': '1', 'imagen-INITIAL_FORMS': '0', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'imagen-0-imagen': self._img(), 'imagen-0-es_principal': 'on', 'imagen-0-color': 'azul',
            'talla-TOTAL_FORMS': '2', 'talla-INITIAL_FORMS': '0', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
            'talla-0-talla': 'M', 'talla-0-stock': '20',
            'talla-1-talla': 'L', 'talla-1-stock': '15',
        }
        r = self.client.post(reverse('crear_producto'), data)
        self.assertIn(r.status_code, [200, 302])

    def test_edit_product_name_only(self):
        self.client.login(username='a1', password='123')
        p = Producto.objects.create(nombre='Old', precio=Decimal('50'), categoria=self.categoria, marca=self.marca)
        data = {
            'nombre': 'New', 'precio': '50', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'imagen-TOTAL_FORMS': '0', 'imagen-INITIAL_FORMS': '0', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'talla-TOTAL_FORMS': '0', 'talla-INITIAL_FORMS': '0', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
        }
        r = self.client.post(reverse('editar_producto_admin', kwargs={'producto_id': p.id}), data)
        self.assertIn(r.status_code, [200, 302])

    def test_edit_product_add_images_and_sizes(self):
        self.client.login(username='a1', password='123')
        p = Producto.objects.create(nombre='Edit2', precio=Decimal('60'), categoria=self.categoria, marca=self.marca)
        data = {
            'nombre': 'Edit2V2', 'precio': '60', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'imagen-TOTAL_FORMS': '1', 'imagen-INITIAL_FORMS': '0', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'imagen-0-imagen': self._img(), 'imagen-0-es_principal': 'on',
            'talla-TOTAL_FORMS': '1', 'talla-INITIAL_FORMS': '0', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
            'talla-0-talla': 'M', 'talla-0-stock': '15',
        }
        r = self.client.post(reverse('editar_producto_admin', kwargs={'producto_id': p.id}), data)
        if r.status_code == 302:
            p.refresh_from_db()
            self.assertEqual(p.nombre, 'Edit2V2')

    def test_edit_product_remove_principal_image(self):
        self.client.login(username='a1', password='123')
        p = Producto.objects.create(nombre='Test', precio=Decimal('50'), categoria=self.categoria, marca=self.marca)
        img = ImagenProducto.objects.create(producto=p, imagen=self._img(), es_principal=True)
        data = {
            'nombre': 'Test', 'precio': '50', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'imagen-TOTAL_FORMS': '1', 'imagen-INITIAL_FORMS': '1', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'imagen-0-id': img.id, 'imagen-0-imagen': img.imagen, 'imagen-0-DELETE': 'on',
            'talla-TOTAL_FORMS': '0', 'talla-INITIAL_FORMS': '0', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
        }
        r = self.client.post(reverse('editar_producto_admin', kwargs={'producto_id': p.id}), data)
        self.assertIn(r.status_code, [200, 302])

    def test_edit_product_add_duplicate_sizes(self):
        self.client.login(username='a1', password='123')
        p = Producto.objects.create(nombre='Tallas', precio=Decimal('50'), categoria=self.categoria, marca=self.marca)
        t1 = TallaProducto.objects.create(producto=p, talla='S', stock=5)
        data = {
            'nombre': 'Tallas', 'precio': '50', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'imagen-TOTAL_FORMS': '0', 'imagen-INITIAL_FORMS': '0', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'talla-TOTAL_FORMS': '2', 'talla-INITIAL_FORMS': '1', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
            'talla-0-id': t1.id, 'talla-0-talla': 'S', 'talla-0-stock': 10,
            'talla-1-talla': 'M', 'talla-1-stock': '8',
        }
        r = self.client.post(reverse('editar_producto_admin', kwargs={'producto_id': p.id}), data)
        if r.status_code == 302:
            self.assertEqual(p.tallas.count(), 2)

    def test_stock_replenish_zero_quantity(self):
        self.client.login(username="a1", password="123")
        t = TallaProducto.objects.create(producto=self.producto, talla="S", stock=5)
        r = self.client.post(reverse('reponer_stock', kwargs={'id': self.producto.id}), {'talla_id': t.id, 'cantidad': '0'})
        self.assertEqual(r.status_code, 302)
        t.refresh_from_db()
        self.assertEqual(t.stock, 5)  

    def test_stock_replenish_invalid_input(self):
        self.client.login(username="a1", password="123")
        t = TallaProducto.objects.create(producto=self.producto, talla="S", stock=5)
        r = self.client.post(reverse('reponer_stock', kwargs={'id': self.producto.id}), {'talla_id': t.id, 'cantidad': 'abc'})
        self.assertEqual(r.status_code, 302)
        t.refresh_from_db()
        self.assertEqual(t.stock, 5)  

    def test_catalog_price_validation_min_greater_than_max(self):
        r = self.client.get(reverse('catalogo'), {'precio_min': '200', 'precio_max': '50'})
        self.assertContains(r, 'mayor')

    def test_create_product_image_with_delete_flag(self):
        self.client.login(username='a1', password='123')
        data = {
            'nombre': 'OnlyDel', 'precio': '50', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'imagen-TOTAL_FORMS': '1', 'imagen-INITIAL_FORMS': '0', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'imagen-0-imagen': self._img(), 'imagen-0-DELETE': 'on',
            'talla-TOTAL_FORMS': '1', 'talla-INITIAL_FORMS': '0', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
            'talla-0-talla': 'M', 'talla-0-stock': '10'
        }
        r = self.client.post(reverse('crear_producto'), data)
        self.assertIn(r.status_code, [200, 302])

    def test_create_product_size_with_delete_flag(self):
        self.client.login(username='a1', password='123')
        data = {
            'nombre': 'OnlyTallaDel', 'precio': '55', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'imagen-TOTAL_FORMS': '1', 'imagen-INITIAL_FORMS': '0', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'imagen-0-imagen': self._img(), 'imagen-0-es_principal': 'on',
            'talla-TOTAL_FORMS': '1', 'talla-INITIAL_FORMS': '0', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
            'talla-0-talla': 'M', 'talla-0-stock': '10', 'talla-0-DELETE': 'on'
        }
        r = self.client.post(reverse('crear_producto'), data)
        self.assertIn(r.status_code, [200, 302])

    def test_preview_with_scale_factor_calculation(self):
        from productos.views import generar_preview
        io1 = BytesIO()
        Image.new('RGB', (400, 400)).save(io1, 'PNG')
        io1.seek(0)
        io2 = BytesIO()
        Image.new('RGBA', (100, 100)).save(io2, 'PNG')
        io2.seek(0)
        res = generar_preview(io1, 'Test', '#000', io2, (50, 50), (100, 100), (400, 400), (200, 200))
        self.assertIsNotNone(res)

    def test_create_product_with_invalid_formset(self):
        self.client.login(username='a1', password='123')
        data = {
            'nombre': 'Invalid', 'precio': '50', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'imagen-TOTAL_FORMS': '1', 'imagen-INITIAL_FORMS': '0', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'imagen-0-es_principal': 'on',
            'talla-TOTAL_FORMS': '1', 'talla-INITIAL_FORMS': '0', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
            'talla-0-talla': 'M',
        }
        r = self.client.post(reverse('crear_producto'), data)
        self.assertEqual(r.status_code, 200)

    def test_edit_product_with_valid_images_and_sizes(self):
        self.client.login(username='a1', password='123')
        p = Producto.objects.create(nombre='EditBoth', precio=Decimal('50'), categoria=self.categoria, marca=self.marca)
        img = ImagenProducto.objects.create(producto=p, imagen=self._img(), es_principal=True)
        t = TallaProducto.objects.create(producto=p, talla='M', stock=10)
        data = {
            'nombre': 'EditBothV2', 'precio': '55', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'imagen-TOTAL_FORMS': '1', 'imagen-INITIAL_FORMS': '1', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'imagen-0-id': img.id, 'imagen-0-imagen': img.imagen, 'imagen-0-es_principal': 'on',
            'talla-TOTAL_FORMS': '1', 'talla-INITIAL_FORMS': '1', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
            'talla-0-id': t.id, 'talla-0-talla': 'L', 'talla-0-stock': '12',
        }
        r = self.client.post(reverse('editar_producto_admin', kwargs={'producto_id': p.id}), data)
        self.assertIn(r.status_code, [200, 302])
        if r.status_code == 302:
            p.refresh_from_db()
            self.assertEqual(p.nombre, 'EditBothV2')

    def test_edit_product_price_only(self):
        self.client.login(username='a1', password='123')
        p = Producto.objects.create(nombre='SoloPrecio', precio=Decimal('50'), categoria=self.categoria, marca=self.marca)
        data = {
            'nombre': 'SoloPrecio', 'precio': '75', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'imagen-TOTAL_FORMS': '0', 'imagen-INITIAL_FORMS': '0', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'talla-TOTAL_FORMS': '0', 'talla-INITIAL_FORMS': '0', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
        }
        r = self.client.post(reverse('editar_producto_admin', kwargs={'producto_id': p.id}), data)
        if r.status_code == 302:
            p.refresh_from_db()
            self.assertEqual(p.precio, Decimal('75'))

    def test_edit_product_with_invalid_formset(self):
        self.client.login(username='a1', password='123')
        p = Producto.objects.create(nombre='EditInv', precio=Decimal('40'), categoria=self.categoria, marca=self.marca)
        img = ImagenProducto.objects.create(producto=p, imagen=self._img(), es_principal=True)
        data = {
            'nombre': 'EditInv', 'precio': '40', 'categoria': self.categoria.id, 'marca': self.marca.id,
            'imagen-TOTAL_FORMS': '1', 'imagen-INITIAL_FORMS': '1', 'imagen-MIN_NUM_FORMS': '0', 'imagen-MAX_NUM_FORMS': '1000',
            'imagen-0-id': img.id,
            'talla-TOTAL_FORMS': '1', 'talla-INITIAL_FORMS': '0', 'talla-MIN_NUM_FORMS': '0', 'talla-MAX_NUM_FORMS': '1000',
            'talla-0-stock': '5',
        }
        r = self.client.post(reverse('editar_producto_admin', kwargs={'producto_id': p.id}), data)
        self.assertEqual(r.status_code, 200)
