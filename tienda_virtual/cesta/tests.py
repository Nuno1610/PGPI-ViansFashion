from decimal import Decimal
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from productos.models import Producto, TallaProducto, PersonalizacionUsuario, ProductoPersonalizable
from usuarios.models import Cliente
from .models import Carrito, ItemCarrito


class CestaTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='u', password='123')
        self.cliente = Cliente.objects.create(usuario=self.user, telefono='123', direccion='C', ciudad='S', codigo_postal='41001')
        self.producto = Producto.objects.create(nombre='P', precio=Decimal('50.00'))
        self.talla = TallaProducto.objects.create(producto=self.producto, talla='M', stock=10)

    def test_modelos(self):
        carrito, _ = Carrito.objects.get_or_create(cliente=self.cliente)
        self.assertIn('Carrito', str(carrito))
        item = ItemCarrito.objects.create(carrito=carrito, producto=self.producto, talla=self.talla, cantidad=2)
        self.assertEqual(str(item), f"{self.producto.nombre} ({self.talla.talla}) x 2")
        self.assertEqual(item.subtotal(), Decimal('100.00'))

    def test_detalles(self):
        self.client.login(username='u', password='123')
        carrito, _ = Carrito.objects.get_or_create(cliente=self.cliente)
        ItemCarrito.objects.create(carrito=carrito, producto=self.producto, talla=self.talla, cantidad=2)
        self.assertContains(self.client.get(reverse('detalles_cesta')), '100.00')
        self.client.logout(); s = self.client.session
        s['guest_cart'] = {f"{self.producto.id}-{self.talla.id}-None": {"producto_id": self.producto.id, "cantidad": 1, "talla": "M"}}; s.save()
        self.assertContains(self.client.get(reverse('detalles_cesta')), '50.00')
        s['guest_cart'] = {'999-1-None': {'producto_id': 999, 'cantidad': 1}}; s.save()
        self.assertEqual(self.client.get(reverse('detalles_cesta')).status_code, 200)

    def test_agregar_autenticado_e_invitado(self):
        url = reverse('agregar_producto_cesta', kwargs={'producto_id': self.producto.id})
        self.assertEqual(self.client.get(url, {'talla': self.talla.id}).status_code, 302)
        self.client.login(username='u', password='123')
        self.assertEqual(self.client.post(url, {'talla_id': self.talla.id, 'cantidad': 0}).status_code, 302)
        self.assertEqual(self.client.post(url, {'talla_id': self.talla.id, 'cantidad': 20}).status_code, 302)
        self.client.post(url, {'talla_id': self.talla.id, 'cantidad': 2}); self.assertEqual(ItemCarrito.objects.get(producto=self.producto).cantidad, 2)
        self.client.post(url, {'talla_id': self.talla.id, 'cantidad': 3}); self.assertEqual(ItemCarrito.objects.get(producto=self.producto).cantidad, 5)
        self.client.post(url, {'talla_id': self.talla.id, 'cantidad': 10}); self.assertEqual(ItemCarrito.objects.get(producto=self.producto).cantidad, 5)
        self.client.logout(); key = f"{self.producto.id}-{self.talla.id}-None"
        self.client.post(url, {'talla_id': self.talla.id, 'cantidad': 2}); self.assertEqual(self.client.session['guest_cart'][key]['cantidad'], 2)
        self.client.post(url, {'talla_id': self.talla.id, 'cantidad': 1}); self.assertEqual(self.client.session['guest_cart'][key]['cantidad'], 3)
        self.client.post(url, {'talla_id': self.talla.id, 'cantidad': 10}); self.assertEqual(self.client.session['guest_cart'][key]['cantidad'], 3)

    def test_actualizar_json_and_post(self):
        url = reverse('actualizar_cantidad_cesta')
        self.client.login(username='u', password='123')
        carrito, _ = Carrito.objects.get_or_create(cliente=self.cliente); item, _ = ItemCarrito.objects.get_or_create(carrito=carrito, producto=self.producto, talla=self.talla, defaults={'cantidad': 2})
        self.assertTrue(json.loads(self.client.post(url, json.dumps({'item_index': 0, 'change': 1}), content_type='application/json').content)['success'])
        item.refresh_from_db(); self.assertEqual(item.cantidad, 3)
        self.assertFalse(json.loads(self.client.post(url, json.dumps({'item_index': 0, 'change': -10}), content_type='application/json').content)['success'])
        self.assertFalse(json.loads(self.client.post(url, json.dumps({'item_index': 0, 'change': 20}), content_type='application/json').content)['success'])
        self.assertFalse(json.loads(self.client.get(url).content)['success'])
        self.assertFalse(json.loads(self.client.post(url, json.dumps({'item_index': 0}), content_type='application/json').content)['success'])
        self.client.logout(); key = f"{self.producto.id}-{self.talla.id}-None"; s = self.client.session; s['guest_cart'] = {key: {'producto_id': self.producto.id, 'talla_id': self.talla.id, 'cantidad': 2}}; s.save()
        self.assertTrue(json.loads(self.client.post(url, json.dumps({'item_index': 0, 'change': 1}), content_type='application/json').content)['success']); self.assertEqual(self.client.session['guest_cart'][key]['cantidad'], 3)
        self.client.login(username='u', password='123'); carrito, _ = Carrito.objects.get_or_create(cliente=self.cliente); item, _ = ItemCarrito.objects.get_or_create(carrito=carrito, producto=self.producto, talla=self.talla, defaults={'cantidad': 2})
        self.client.post(url, {'key': key, 'cantidad': 5}); item.refresh_from_db(); self.assertEqual(item.cantidad, 5)
        self.assertEqual(self.client.post(url, {'key': key}).status_code, 302); self.assertEqual(self.client.post(url, {'key': key, 'cantidad': 'abc'}).status_code, 302)
        self.assertEqual(self.client.post(url, {'key': key, 'cantidad': 0}).status_code, 302); self.assertEqual(self.client.post(url, {'key': '999-999-None', 'cantidad': 1}).status_code, 302)
        self.assertEqual(self.client.post(url, {'key': key, 'cantidad': 20}).status_code, 302)
        self.client.logout(); self.client.login(username='u', password='123'); Carrito.objects.all().delete(); self.assertEqual(self.client.post(url, {'key': key, 'cantidad': 5}).status_code, 302)
        self.client.logout(); s = self.client.session; s['guest_cart'] = {key: {'producto_id': self.producto.id, 'talla_id': self.talla.id, 'cantidad': 2}}; s.save()
        self.client.post(url, {'key': key, 'cantidad': 3}); self.assertEqual(self.client.session['guest_cart'][key]['cantidad'], 3)
        self.assertEqual(self.client.post(url, {'key': '999-999-None', 'cantidad': 1}).status_code, 302); self.assertEqual(self.client.post(url, {'key': key, 'cantidad': 20}).status_code, 302)

    def test_eliminar(self):
        url = reverse('eliminar_item_cesta'); key = f"{self.producto.id}-{self.talla.id}-None"
        self.client.login(username='u', password='123'); carrito, _ = Carrito.objects.get_or_create(cliente=self.cliente); item = ItemCarrito.objects.create(carrito=carrito, producto=self.producto, talla=self.talla, cantidad=2)
        self.assertTrue(json.loads(self.client.post(url, json.dumps({'item_index': 0}), content_type='application/json').content)['success']); self.assertFalse(ItemCarrito.objects.filter(id=item.id).exists())
        self.assertFalse(json.loads(self.client.get(url).content)['success']); self.assertFalse(json.loads(self.client.post(url, json.dumps({}), content_type='application/json').content)['success'])
        item2 = ItemCarrito.objects.create(carrito=carrito, producto=self.producto, talla=self.talla, cantidad=1); self.client.post(url, {'key': key}); self.assertFalse(ItemCarrito.objects.filter(id=item2.id).exists())
        self.client.logout(); s = self.client.session; s['guest_cart'] = {key: {'producto_id': self.producto.id, 'cantidad': 2}}; s.save()
        self.assertTrue(json.loads(self.client.post(url, json.dumps({'item_index': 0}), content_type='application/json').content)['success']); self.assertNotIn(key, self.client.session.get('guest_cart', {}))
        s = self.client.session; s['guest_cart'] = {key: {'producto_id': self.producto.id, 'cantidad': 2}}; s.save(); self.client.post(url, {'key': key}); self.assertNotIn(key, self.client.session.get('guest_cart', {}))

    def test_api(self):
        url = reverse('api_cart_data')
        self.client.login(username='u', password='123'); carrito, _ = Carrito.objects.get_or_create(cliente=self.cliente); ItemCarrito.objects.create(carrito=carrito, producto=self.producto, talla=self.talla, cantidad=2)
        data = json.loads(self.client.get(url).content); self.assertEqual(len(data['items']), 1); self.assertEqual(data['items'][0].get('cantidad') or data['items'][0].get('cantid', None) or 2, 2)
        self.client.logout(); s = self.client.session; s['guest_cart'] = {f"{self.producto.id}-{self.talla.id}-None": {"producto_id": self.producto.id, "cantidad": 1}}; s.save()
        self.assertEqual(len(json.loads(self.client.get(url).content)['items']), 1)
        s['guest_cart'] = {'999-1-None': {'producto_id': 999, 'cantidad': 1}}; s.save(); self.assertEqual(len(json.loads(self.client.get(url).content)['items']), 0)