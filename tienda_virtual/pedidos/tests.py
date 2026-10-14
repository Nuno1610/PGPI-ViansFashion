from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from decimal import Decimal
from .models import Pedido, ItemPedido
from usuarios.models import Cliente
from productos.models import Producto, Categoria, TallaProducto
from cesta.models import Carrito, ItemCarrito


class PedidosTestCase(TestCase):
    
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', email='test@test.com', password='pass123',
            first_name='Test', last_name='User')
        self.cliente = Cliente.objects.create(
            usuario=self.user, telefono='600123456', direccion='Calle Test 123',
            ciudad='Madrid', codigo_postal='28001')
        self.admin = User.objects.create_superuser('adminpedidos', 'adminpedidos@test.com', 'admin123')
        self.cat = Categoria.objects.create(nombre='Ropa', slug='ropa')
        self.prod = Producto.objects.create(
            nombre='Camiseta Test', descripcion='Test', precio=Decimal('29.99'),
            categoria=self.cat, es_visible=True)
        self.talla = TallaProducto.objects.create(producto=self.prod, talla='M', stock=5)
        self.carrito = Carrito.objects.create(cliente=self.cliente)
        ItemCarrito.objects.create(carrito=self.carrito, producto=self.prod,
            talla=self.talla, cantidad=2)
        self.pedido = Pedido.objects.create(
            cliente=self.cliente, nombre_cliente='Test User', email='test@test.com',
            numero_pedido='VFF-000001', estado='ENRV', metodo_pago='stripe',
            direccion_envio='Calle Test 123', telefono='600123456')
        ItemPedido.objects.create(pedido=self.pedido, producto=self.prod,
            talla='M', cantidad=2, precio_unitario=Decimal('29.99'))
    
    def test_modelos(self):
        
        self.assertEqual(str(self.pedido), f"Pedido {self.pedido.numero_pedido} - {self.cliente}")
        self.assertEqual(self.pedido.subtotal, Decimal('59.98'))
        self.pedido.impuestos = Decimal('10.00')
        self.pedido.coste_entrega = Decimal('5.00')
        self.pedido.descuento = Decimal('3.00')
        self.assertEqual(self.pedido.total, Decimal('71.98'))
        item = self.pedido.items.first()
        self.assertEqual(str(item), "2 x Camiseta Test (M)")
        item.cantidad = 3
        item.save()
        self.assertEqual(item.total, Decimal('89.97'))
    
    def test_crear_pedido_autenticado(self):
        
        self.client.login(username='testuser', password='pass123')
        r = self.client.get(reverse('crear_pedido'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['items']), 1)
        self.carrito.items.all().delete()
        self.assertEqual(len(self.client.get(reverse('crear_pedido')).context['items']), 0)
    
    @patch('stripe.PaymentIntent.create')
    def test_crear_pedido_autenticado_post(self, mock_stripe):
        
        mock_stripe.return_value = MagicMock(id='pi_auth123', client_secret='secret_auth')
        Cliente.nombre = property(lambda s: f"{s.usuario.first_name} {s.usuario.last_name}")
        Cliente.email = property(lambda s: s.usuario.email)
        try:
            self.carrito.items.all().delete()
            ItemCarrito.objects.create(carrito=self.carrito, producto=self.prod,
                talla=self.talla, cantidad=3)
            self.client.login(username='testuser', password='pass123')
            r = self.client.post(reverse('crear_pedido'), {
                'nombre': 'Test User',
                'email': 'test@test.com',
                'direccion': 'Nueva Direccion',
                'telefono': '600123456',
                'cp': '28001'
            })
            self.assertTrue(r.context['show_payment'])
            p = Pedido.objects.latest('fecha_creacion')
            self.assertEqual(p.nombre_cliente, 'Test User')
            self.assertEqual(p.items.count(), 1)
            self.assertEqual(p.items.first().cantidad, 3)
        finally:
            delattr(Cliente, 'nombre')
            delattr(Cliente, 'email')
    
    @patch('stripe.PaymentIntent.create')
    def test_crear_pedido_invitado(self, mock_stripe):
        
        mock_stripe.return_value = MagicMock(id='pi_guest123', client_secret='secret_guest')
        s = self.client.session
        s['guest_cart'] = {f'{self.prod.id}-{self.talla.id}-None': {'cantidad': 1}}
        s.save()
        self.assertEqual(len(self.client.get(reverse('crear_pedido')).context['items']), 1)
        s['guest_cart'] = {'999-999-None': {'cantidad': 1}}
        s.save()
        self.assertEqual(len(self.client.get(reverse('crear_pedido')).context['items']), 0)
        s['guest_cart'] = {f'{self.prod.id}-{self.talla.id}-None': {'cantidad': 2}}
        s.save()
        r = self.client.post(reverse('crear_pedido'), {
            'nombre': 'Guest', 'email': 'g@t.com', 'telefono': '600123456', 'cp': '28001', 'direccion': 'Addr'})
        self.assertTrue(r.context['show_payment'])
        p = Pedido.objects.latest('fecha_creacion')
        self.assertIsNone(p.cliente)
        self.assertEqual(p.items.count(), 1)
        self.assertEqual(p.items.first().cantidad, 2)
        s['guest_cart'] = {}
        s.save()
        r = self.client.post(reverse('crear_pedido'),
            {'nombre': 'T', 'email': 't@t.com', 'telefono': '600123456', 'cp': '28001', 'direccion': 'A'})
        self.assertRedirects(r, reverse('detalles_cesta'))
    
    def test_checkout(self):
        
        
        self.client.login(username='testuser', password='pass123')
        r = self.client.get(reverse('checkout'))
        self.assertEqual(len(r.context['items']), 1)
        self.carrito.items.all().delete()
        r = self.client.get(reverse('checkout'))
        self.assertRedirects(r, reverse('detalles_cesta'))
        
        
        self.client.logout()
        s = self.client.session
        s['guest_cart'] = {f'{self.prod.id}-{self.talla.id}-None': {'cantidad': 2}}
        s.save()
        r = self.client.get(reverse('checkout'))
        self.assertEqual(len(r.context['items']), 1)
        
        s['guest_cart'] = {'999-999-None': {'cantidad': 1}}
        s.save()
        r = self.client.get(reverse('checkout'))
        self.assertEqual(len(r.context['items']), 0)
        
        s['guest_cart'] = {}
        s.save()
        r = self.client.get(reverse('checkout'))
        self.assertRedirects(r, reverse('detalles_cesta'))
    
    @patch('stripe.PaymentIntent.retrieve')
    @patch('pedidos.views.enviar_factura_por_email')
    def test_pedido_completado(self, mock_email, mock_stripe):
        
        mock_stripe.return_value = MagicMock(status='succeeded')
        self.pedido.stripe_payment_intent = 'pi_test123'
        self.pedido.pago_completado = False
        self.pedido.save()
        self.client.login(username='testuser', password='pass123')
        self.client.get(reverse('pedido_completado', args=[self.pedido.numero_pedido]))
        self.pedido.refresh_from_db()
        self.assertTrue(self.pedido.pago_completado)
        mock_email.assert_called_once()
        self.assertEqual(self.carrito.items.count(), 0)
        p2 = Pedido.objects.create(cliente=self.cliente, nombre_cliente='U', email='e@t.com',
            numero_pedido='VFF-999', estado='ENRV', metodo_pago='stripe',
            direccion_envio='A', telefono='600')
        self.assertEqual(self.client.get(reverse('pedido_completado', args=[p2.numero_pedido])).status_code, 200)
        p3 = Pedido.objects.create(cliente=None, nombre_cliente='G', email='g@t.com',
            numero_pedido='VFF-998', estado='ENRV', metodo_pago='stripe',
            direccion_envio='GA', telefono='601', stripe_payment_intent='pi_g')
        self.client.logout()
        s = self.client.session
        s['guest_cart'] = {f'{self.prod.id}-{self.talla.id}': {'cantidad': 1}}
        s.save()
        self.client.get(reverse('pedido_completado', args=[p3.numero_pedido]))
        self.assertEqual(self.client.session.get('guest_cart'), {})
    
    def test_admin_listar_y_cancelar(self):
        
        self.client.login(username='adminpedidos', password='admin123')
        Pedido.objects.create(cliente=self.cliente, nombre_cliente='U2', email='u2@t.com',
            numero_pedido='VFF-000002', estado='PROC', metodo_pago='stripe',
            direccion_envio='A2', telefono='600000002')
        self.assertEqual(self.client.get(reverse('listar_pedidos')).context['pedidos'].count(), 2)
        self.client.get(reverse('cancelar_pedido', args=[self.pedido.id]))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'CANC')
        self.pedido.estado = 'ENVI'
        self.pedido.save()
        self.client.get(reverse('cancelar_pedido', args=[self.pedido.id]))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'ENVI')
    
    def test_mis_pedidos_y_detalle(self):
        
        self.client.login(username='testuser', password='pass123')
        r = self.client.get(reverse('mis_pedidos'))
        self.assertEqual(len(r.context['pedidos']), 1)
        r = self.client.get(reverse('detalle_pedido', args=[self.pedido.numero_pedido]))
        self.assertEqual(r.context['pedido'], self.pedido)
        self.client.logout()
        self.assertEqual(len(self.client.get(reverse('mis_pedidos')).context['pedidos']), 0)
    
    def test_seguimiento_pedido(self):
        
        self.client.login(username='testuser', password='pass123')
        self.assertEqual(self.client.get(reverse('seguimiento_pedido',
            args=[self.pedido.numero_pedido])).status_code, 200)
        self.client.login(username='adminpedidos', password='admin123')
        self.assertEqual(self.client.get(reverse('seguimiento_pedido',
            args=[self.pedido.numero_pedido])).status_code, 200)
        User.objects.create_user('otro', 'otro@test.com', 'pass')
        self.client.login(username='otro', password='pass')
        self.assertContains(self.client.get(reverse('seguimiento_pedido',
            args=[self.pedido.numero_pedido])), 'No es posible acceder')
        self.client.logout()
        self.assertContains(self.client.get(reverse('seguimiento_pedido',
            args=[self.pedido.numero_pedido])), 'No es posible acceder')
    
    def test_buscar_pedido_anonimo(self):
        
        Pedido.objects.create(cliente=None, nombre_cliente='Guest', email='g@t.com',
            numero_pedido='VFF-000999', estado='ENRV', metodo_pago='stripe',
            direccion_envio='GAddr', telefono='600999999')
        self.assertEqual(self.client.get(reverse('buscar_pedido_anonimo')).status_code, 200)
        self.assertContains(self.client.post(reverse('buscar_pedido_anonimo'),
            {'numero_pedido': 'VFF-000999'}), 'VFF-000999')
        self.assertContains(self.client.post(reverse('buscar_pedido_anonimo'),
            {'numero_pedido': 'VFF-000001'}), 'No es posible acceder')
        self.client.login(username='testuser', password='pass123')
        self.assertContains(self.client.post(reverse('buscar_pedido_anonimo'),
            {'numero_pedido': 'VFF-000001'}), 'VFF-000001')
        self.client.logout()
        self.assertContains(self.client.post(reverse('buscar_pedido_anonimo'),
            {'numero_pedido': ''}), 'ingresa el número')
        self.assertContains(self.client.post(reverse('buscar_pedido_anonimo'),
            {'numero_pedido': 'XXX'}), 'No se encontró')
    
    def test_generar_factura_pdf(self):
        
        from pedidos.views import generar_factura_pdf
        pdf_content = generar_factura_pdf(self.pedido, self.pedido.items.all()).getvalue()
        self.assertGreater(len(pdf_content), 0)
        self.assertTrue(pdf_content.startswith(b'%PDF'))
    
    @patch('pedidos.views.EmailMultiAlternatives')
    @patch('pedidos.views.generar_factura_pdf')
    def test_enviar_factura_email(self, mock_pdf, mock_email):
        
        from pedidos.views import enviar_factura_por_email
        from io import BytesIO
        mock_pdf.return_value = BytesIO(b'PDF_CONTENT')
        mock_email_instance = MagicMock()
        mock_email.return_value = mock_email_instance
        enviar_factura_por_email(self.pedido, self.pedido.items.all())
        mock_pdf.assert_called_once()
        mock_email_instance.send.assert_called_once()

    def test_detalle_pedido_admin_y_cambiar_estado(self):
        self.client.login(username='adminpedidos', password='admin123')
        r = self.client.get(reverse('detalle_pedido_admin', args=[self.pedido.numero_pedido]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['pedido'], self.pedido)

        r = self.client.post(reverse('cambiar_estado_pedido', args=[self.pedido.id]), {'nuevo_estado': 'ENVI'})
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'ENVI')

        r = self.client.post(reverse('cambiar_estado_pedido', args=[self.pedido.id]), {'nuevo_estado': 'BAD'})
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'ENVI')

    def test_buscar_pedido_anonimo_superuser(self):
        self.client.login(username='adminpedidos', password='admin123')
        r = self.client.post(reverse('buscar_pedido_anonimo'), {'numero_pedido': self.pedido.numero_pedido})
        self.assertContains(r, self.pedido.numero_pedido)
