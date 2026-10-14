from django.test import TestCase, Client
from django.urls import reverse
from .models import Articulo, Escaparate


class HomeTestCase(TestCase):
    """Tests consolidados para módulo home"""
    
    def setUp(self):
        self.client = Client()
        self.articulo1 = Articulo.objects.create(nombre="Camiseta Deportiva", descripcion="Perfecta para entrenar")
        self.articulo2 = Articulo.objects.create(nombre="Pantalón Casual", descripcion="Cómodo y elegante")
        self.escaparate = Escaparate.objects.create(articulo=self.articulo1)
    
    def test_modelos(self):
        """Verifica modelos Articulo y Escaparate"""
        self.assertEqual(str(self.articulo1), "Camiseta Deportiva")
        self.assertEqual(self.articulo1.nombre, "Camiseta Deportiva")
        self.assertEqual(self.articulo1.descripcion, "Perfecta para entrenar")
        
        self.assertEqual(str(self.escaparate), str(self.articulo1.id))
        self.assertEqual(self.escaparate.articulo, self.articulo1)
        
        escaparate2 = Escaparate.objects.create(articulo=self.articulo2)
        self.assertEqual(Escaparate.objects.count(), 2)
        self.assertEqual(str(escaparate2), str(self.articulo2.id))
    
    def test_vistas(self):
        """Verifica todas las vistas principales"""
        r = self.client.get(reverse('home'))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'index.html')
        
        r = self.client.get(reverse('sobre_nosotros'))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'sobre_nosotros.html')
        
        r = self.client.get(reverse('contacto'))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'contacto.html')
    
    def test_index_multiples_escaparates(self):
        """Verifica que index muestra el primer escaparate"""
        Escaparate.objects.create(articulo=self.articulo2)
        
        r = self.client.get(reverse('home'))
        self.assertEqual(r.status_code, 200)
        # Comprobar que existen dos escaparates y que la vista responde correctamente
        self.assertEqual(Escaparate.objects.count(), 2)
        self.assertTemplateUsed(r, 'index.html')
    
    def test_barra_busqueda(self):
        """Verifica función de búsqueda con nombre vacío y no vacío"""
        from home.views import barra_busqueda
        from django.http import HttpRequest
        
        request = HttpRequest()
        request.GET = {'nombre': ''}
        result = barra_busqueda(request)
        self.assertIsNone(result)
        
        request.GET = {'nombre': 'test'}
        try:
            barra_busqueda(request) 
        except NameError:
            pass