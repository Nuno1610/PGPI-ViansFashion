from django.urls import path
from . import views

urlpatterns = [
    path('catalogo/', views.catalogo, name='catalogo'),
    path("catalogo/<slug:categoria_slug>/", views.catalogo, name="catalogo_categoria"),
    path("producto/<int:id>/", views.detalle_producto, name="detalle_producto"),
    path('producto/<int:id>/reponer/', views.reponer_stock, name='reponer_stock'),
    path('producto/<int:id>/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    path('personalizar/<int:producto_id>/', views.personalizar_producto, name='personalizar_producto'),
    path('personalizar/preview/<int:pk>/', views.producto_personalizado_preview, name='producto_personalizado_preview'),
    path('admin/categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('admin/categorias/<int:categoria_id>/editar/', views.editar_categoria, name='editar_categoria'),
    path('admin/categorias/<int:categoria_id>/eliminar/', views.eliminar_categoria, name='eliminar_categoria'),
    path('admin/producto/crear/', views.crear_producto, name='crear_producto'),
    path('admin/producto/<int:producto_id>/editar/', views.editar_producto_admin, name='editar_producto_admin'),
    path('admin/producto/<int:producto_id>/imagen/agregar/', views.agregar_imagen_producto, name='agregar_imagen_producto'),
    path('admin/producto/<int:producto_id>/talla/agregar/', views.agregar_talla_producto, name='agregar_talla_producto'),
    path('admin/marca/crear/', views.crear_marca, name='crear_marca'),
    path('admin/marca/editar/<int:marca_id>/', views.editar_marca, name='editar_marca'),
    path('admin/marca/eliminar/<int:marca_id>/', views.eliminar_marca, name='eliminar_marca'),
]
