from django.urls import path
from . import views

urlpatterns = [
   path('mis_pedidos/', views.mis_pedidos, name='mis_pedidos'),
   path('pedidos/', views.listar_pedidos, name='listar_pedidos'),
   path('pedidos/cancelar/<int:pedido_id>/', views.cancelar_pedido, name='cancelar_pedido'),
   path('pedidos/aceptar/<int:pedido_id>/', views.aceptar_pedido, name='aceptar_pedido'),
   path("checkout/", views.checkout, name="checkout"),
   path('crear/', views.crear_pedido, name='crear_pedido'),
   path('completado/<str:numero_pedido>/', views.pedido_completado, name='pedido_completado'),
   path('pedido/<str:numero_pedido>/', views.detalle_pedido, name='detalle_pedido'),
   path('pedido/<str:numero_pedido>/seguimiento/', views.seguimiento_pedido, name='seguimiento_pedido'),
   path('buscar-pedido/', views.buscar_pedido_anonimo, name='buscar_pedido_anonimo'),
   path('pedido/admin/<str:numero_pedido>/', views.detalle_pedido_admin, name='detalle_pedido_admin'),
   path('pedido/admin/<int:pedido_id>/cambiar_estado/', views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
]