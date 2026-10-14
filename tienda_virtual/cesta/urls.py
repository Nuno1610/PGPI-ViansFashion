from django.urls import path
from . import views


urlpatterns = [
    path('detalles/', views.detalles_cesta, name='detalles_cesta'),
    path("agregar/<int:producto_id>/", views.agregar_producto_cesta, name="agregar_producto_cesta"),
    path("detalles/actualizar-cantidad/", views.actualizar_cantidad_cesta, name="actualizar_cantidad_cesta"),
    path("detalles/eliminar-item/", views.eliminar_producto_cesta, name="eliminar_item_cesta"),
    path("api/cart-data/", views.api_cart_data, name="api_cart_data"),
]