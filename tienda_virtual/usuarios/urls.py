from django.urls import path
from . import views

urlpatterns = [
    path('registro/', views.registro_cliente, name='registro_cliente'),
    path('login/', views.iniciar_sesion, name='iniciar_sesion'),
    path('logout/', views.cerrar_sesion, name='cerrar_sesion'),
    path('clientes/', views.listar_clientes, name="gestor_clientes"),
    path('eliminar/<int:cliente_id>/', views.eliminar_cliente, name='eliminar_cliente'),
]