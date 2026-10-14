from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.messages import get_messages
from usuarios.models import Cliente
from usuarios.forms import RegistroClienteForm, LoginClienteForm


class ClienteModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', first_name='Juan', last_name='Pérez', email='juan@test.com', password='testpass123')
        self.cliente = Cliente.objects.create(usuario=self.user, telefono='123456789', direccion='Calle Test 123', ciudad='Sevilla', codigo_postal='41001')
    
    def test_cliente_creation_and_str(self):
        self.assertEqual(self.cliente.usuario.username, 'testuser')
        self.assertEqual(self.cliente.telefono, '123456789')
        self.assertEqual(str(self.cliente), 'Juan Pérez')
        self.assertIsNotNone(self.cliente.fecha_creacion)
    
    def test_cliente_usuario_relationship(self):
        self.assertEqual(self.cliente.usuario, self.user)
        self.assertEqual(self.user.cliente, self.cliente)
    
    def test_cliente_deletion_with_user(self):
        cliente_id = self.cliente.id
        self.user.delete()
        self.assertFalse(Cliente.objects.filter(id=cliente_id).exists())


class RegistroClienteFormTest(TestCase):
    def get_valid_form_data(self, **kwargs):
        data = {'username': 'newuser', 'first_name': 'María', 'last_name': 'García', 'email': 'maria@test.com',
                'password1': 'TestPass123!', 'password2': 'TestPass123!', 'telefono': '987654321',
                'direccion': 'Avenida Test 456', 'ciudad': 'Madrid', 'codigo_postal': '28001'}
        data.update(kwargs)
        return data
    
    def test_registro_form_valid(self):
        form = RegistroClienteForm(data=self.get_valid_form_data())
        self.assertTrue(form.is_valid())
    
    def test_registro_form_invalid_telefono(self):
        form = RegistroClienteForm(data=self.get_valid_form_data(telefono='98765ABC1'))
        self.assertFalse(form.is_valid())
        self.assertIn('telefono', form.errors)
    
    def test_registro_form_invalid_codigo_postal(self):
        form = RegistroClienteForm(data=self.get_valid_form_data(codigo_postal='28A01'))
        self.assertFalse(form.is_valid())
        self.assertIn('codigo_postal', form.errors)
    
    def test_registro_form_passwords_not_match(self):
        form = RegistroClienteForm(data=self.get_valid_form_data(password2='DifferentPass123!'))
        self.assertFalse(form.is_valid())
    
    def test_registro_form_save(self):
        form = RegistroClienteForm(data=self.get_valid_form_data())
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(User.objects.filter(username='newuser').exists())
        self.assertTrue(Cliente.objects.filter(usuario=user).exists())
        cliente = Cliente.objects.get(usuario=user)
        self.assertEqual(cliente.telefono, '987654321')
    
    def test_registro_form_missing_fields(self):
        form = RegistroClienteForm(data={'username': 'newuser', 'password1': 'TestPass123!', 'password2': 'TestPass123!'})
        self.assertFalse(form.is_valid())


class LoginClienteFormTest(TestCase):
    def test_login_form_valid(self):
        form = LoginClienteForm(data={'email': 'test@test.com', 'password': 'testpass123'})
        self.assertTrue(form.is_valid())
    
    def test_login_form_invalid_email(self):
        form = LoginClienteForm(data={'email': 'invalid-email', 'password': 'testpass123'})
        self.assertFalse(form.is_valid())
    
    def test_login_form_missing_password(self):
        form = LoginClienteForm(data={'email': 'test@test.com'})
        self.assertFalse(form.is_valid())


class RegistroClienteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('registro_cliente')
    
    def test_registro_view_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/registro_cliente.html')
        self.assertIsInstance(response.context['form'], RegistroClienteForm)
    
    def test_registro_view_post_valid(self):
        form_data = {'username': 'newuser', 'first_name': 'Pedro', 'last_name': 'Sánchez', 'email': 'pedro@test.com',
                     'password1': 'TestPass123!', 'password2': 'TestPass123!', 'telefono': '111222333',
                     'direccion': 'Calle Nueva 789', 'ciudad': 'Barcelona', 'codigo_postal': '08001'}
        response = self.client.post(self.url, data=form_data)
        self.assertRedirects(response, reverse('iniciar_sesion'))
        self.assertTrue(User.objects.filter(username='newuser').exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('Tu cuenta ha sido creada con éxito', str(messages[0]))
    
    def test_registro_view_post_invalid(self):
        response = self.client.post(self.url, data={'username': 'newuser', 'email': 'invalid-email', 'password1': 'TestPass123!', 'password2': 'Different123!'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())


class IniciarSesionViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('iniciar_sesion')
        self.user = User.objects.create_user(username='testuser', email='test@test.com', password='testpass123')
        Cliente.objects.create(usuario=self.user, telefono='123456789', direccion='Calle Test', ciudad='Sevilla', codigo_postal='41001')
    
    def test_iniciar_sesion_view_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/login.html')
        self.assertIsInstance(response.context['form'], LoginClienteForm)
    
    def test_iniciar_sesion_post_valid(self):
        response = self.client.post(self.url, data={'email': 'test@test.com', 'password': 'testpass123'})
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    def test_iniciar_sesion_post_invalid_password(self):
        response = self.client.post(self.url, data={'email': 'test@test.com', 'password': 'wrongpassword'})
        self.assertRedirects(response, reverse('iniciar_sesion'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('incorrectos' in str(msg) for msg in messages))
    
    def test_iniciar_sesion_post_nonexistent_email(self):
        response = self.client.post(self.url, data={'email': 'noexiste@test.com', 'password': 'testpass123'})
        self.assertRedirects(response, reverse('iniciar_sesion'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No existe una cuenta' in str(msg) for msg in messages))
    
    def test_iniciar_sesion_post_invalid_form(self):
        response = self.client.post(self.url, data={'email': 'invalid-email', 'password': 'testpass123'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/login.html')


class CerrarSesionViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('cerrar_sesion')
        self.user = User.objects.create_user(username='testuser', email='test@test.com', password='testpass123')
    
    def test_cerrar_sesion(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('home'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('cerrado sesión' in str(msg) for msg in messages))
        response = self.client.get(reverse('home'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class ListarClientesViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('gestor_clientes')
        self.normal_user = User.objects.create_user(username='normaluser_list', email='normallist@test.com', password='testpass123')
        Cliente.objects.create(usuario=self.normal_user, telefono='111111111', direccion='Calle Normal', ciudad='Madrid', codigo_postal='28001')
        self.admin_user = User.objects.create_superuser(username='adminlist', email='adminlist@test.com', password='adminpass123')
        Cliente.objects.create(usuario=self.admin_user, telefono='222222222', direccion='Calle Admin', ciudad='Barcelona', codigo_postal='08001')
    
    def test_listar_clientes_no_authenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_listar_clientes_normal_user(self):
        self.client.login(username='normaluser_list', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
    
    def test_listar_clientes_admin_user(self):
        self.client.login(username='adminlist', password='adminpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/gestor_clientes.html')
        self.assertEqual(len(response.context['clientes']), 2)


class EliminarClienteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.normal_user = User.objects.create_user(username='normaluser_del', email='normaldel@test.com', password='testpass123')
        self.cliente_normal = Cliente.objects.create(usuario=self.normal_user, telefono='111111111', direccion='Calle Normal', ciudad='Madrid', codigo_postal='28001')
        self.admin_user = User.objects.create_superuser(username='admindel', email='admindel@test.com', password='adminpass123')
        Cliente.objects.create(usuario=self.admin_user, telefono='222222222', direccion='Calle Admin', ciudad='Barcelona', codigo_postal='08001')
        self.user_to_delete = User.objects.create_user(username='usertodelete', email='delete@test.com', password='testpass123')
        self.cliente_to_delete = Cliente.objects.create(usuario=self.user_to_delete, telefono='333333333', direccion='Calle Delete', ciudad='Valencia', codigo_postal='46001')
    
    def test_eliminar_cliente_no_authenticated(self):
        url = reverse('eliminar_cliente', args=[self.cliente_to_delete.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Cliente.objects.filter(id=self.cliente_to_delete.id).exists())
    
    def test_eliminar_cliente_normal_user(self):
        self.client.login(username='normaluser_del', password='testpass123')
        url = reverse('eliminar_cliente', args=[self.cliente_to_delete.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Cliente.objects.filter(id=self.cliente_to_delete.id).exists())
    
    def test_eliminar_cliente_admin_user(self):
        self.client.login(username='admindel', password='adminpass123')
        url = reverse('eliminar_cliente', args=[self.cliente_to_delete.id])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('gestor_clientes'))
        self.assertFalse(Cliente.objects.filter(id=self.cliente_to_delete.id).exists())
        self.assertFalse(User.objects.filter(username='usertodelete').exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('eliminado correctamente' in str(msg) for msg in messages))
    
    def test_eliminar_cliente_nonexistent(self):
        self.client.login(username='admindel', password='adminpass123')
        url = reverse('eliminar_cliente', args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class AdminTest(TestCase):
    def test_cliente_admin_registered(self):
        from django.contrib import admin
        from usuarios.models import Cliente
        self.assertIn(Cliente, admin.site._registry)
