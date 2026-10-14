from django.shortcuts import render, redirect, get_object_or_404
from .models import Producto, TallaProducto, ItemCarrito, Carrito, PersonalizacionUsuario
from usuarios.models import Cliente
from django.contrib import messages
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse

def detalles_cesta(request):
    items = []
    total_final = 0

    if request.user.is_authenticated:
        # Carrito del usuario registrado
        carrito = Carrito.objects.filter(cliente__usuario=request.user).first()
        if carrito:
            for item in carrito.items.all():
                subtotal = item.producto.precio * item.cantidad
                total_final += subtotal
                items.append({
                    "producto": item.producto,
                    "talla": item.talla,
                    "cantidad": item.cantidad,
                    "subtotal": f"{subtotal:.2f}",
                    "key": f"{item.producto.id}-{item.talla.id}-{item.personalizacion.id if item.personalizacion else 0}",  # clave temporal para los botones
                    "personalizacion_id": item.personalizacion.id if item.personalizacion else "None",
                    "preview_url": item.personalizacion.imagen_generada.url if item.personalizacion else "None"
                })
    else:
        # Carrito de invitado en sesión
        carrito = request.session.get("guest_cart", {})
        for key, valor in carrito.items():
            producto_id = valor["producto_id"]
            cantidad = valor["cantidad"]
            talla = valor.get("talla", "")
            try:
                producto = Producto.objects.get(id=producto_id)
            except Producto.DoesNotExist:
                continue
            subtotal = producto.precio * cantidad
            total_final += subtotal
            items.append({
                "producto": producto,
                "talla": talla,
                "cantidad": cantidad,
                "subtotal": f"{subtotal:.2f}",
                "key": key,
                "personalizacion_id": valor.get("personalizacion_id"),
                "preview_url": valor.get("preview_url")
            })

    total_final = f"{total_final:.2f}"

    return render(request, "cesta/detalles.html", {
        "items": items,
        "total_final": total_final
    })

def agregar_producto_cesta(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    talla_id = request.POST.get("talla_id") or request.GET.get("talla")
    cantidad = int(request.POST.get("cantidad", 1))
    personalizacion_id = request.GET.get("personalizacion_id")

    personalizacion = None
    if personalizacion_id:
        personalizacion = get_object_or_404(PersonalizacionUsuario, id=personalizacion_id)

    talla = get_object_or_404(TallaProducto, id=talla_id)

    # Validaciones de stock
    if cantidad < 1:
        messages.error(request, "La cantidad debe ser al menos 1.")
        return redirect("detalle_producto", id=producto.id)
    if cantidad > talla.stock:
        messages.error(request, f"No hay suficiente stock para la talla {talla.talla}.")
        return redirect("detalle_producto", id=producto.id)

    # Usuario registrado
    if request.user.is_authenticated:
        cliente = Cliente.objects.get(usuario=request.user)
        carrito, _ = Carrito.objects.get_or_create(cliente=cliente)
        item, created = ItemCarrito.objects.get_or_create(
            carrito=carrito,
            producto=producto,
            talla=talla,
            personalizacion=personalizacion,
            defaults={"cantidad": cantidad}
        )
        if not created:
            if item.cantidad + cantidad > talla.stock:
                messages.error(request, f"No hay suficiente stock para la talla {talla.talla}")
                return redirect("detalle_producto", id=producto.id)
            item.cantidad += cantidad
            item.save()
    else:
        # Invitado en sesión
        guest_cart = request.session.get("guest_cart", {})
        key = f"{producto_id}-{talla_id}-{personalizacion_id or 'None'}"
        if key in guest_cart:
            if guest_cart[key]["cantidad"] + cantidad > talla.stock:
                messages.error(request, f"No hay suficiente stock para la talla {talla.talla}")
                return redirect("detalle_producto", id=producto.id)
            guest_cart[key]["cantidad"] += cantidad
        else:
            guest_cart[key] = {
                "producto_id": producto.id,
                "producto_nombre": producto.nombre,
                "talla": talla.talla,
                "talla_id": talla.id,
                "cantidad": cantidad,
                "precio": float(producto.precio),
                "personalizacion_id": personalizacion.id if personalizacion else None,
                "preview_url": personalizacion.imagen_generada.url if personalizacion else None
            }
        request.session["guest_cart"] = guest_cart
        request.session.modified = True

    messages.success(request, "Producto añadido al carrito.")
    return redirect("detalles_cesta")

    
def actualizar_cantidad_cesta(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"})

    # Manejar solicitudes JSON (AJAX)
    try:
        import json
        data = json.loads(request.body)
        item_index = data.get("item_index")
        change = data.get("change", 0)
        
        if item_index is not None and change != 0:
            # Obtener lista actual de items
            items = []
            
            if request.user.is_authenticated:
                carrito = Carrito.objects.filter(cliente__usuario=request.user).first()
                if carrito:
                    for item in carrito.items.all():
                        items.append({
                            "producto_id": item.producto.id,
                            "talla_id": item.talla.id,
                            "cantidad": item.cantidad,
                            "object": item
                        })
            else:
                guest_cart = request.session.get("guest_cart", {})
                for key, valor in guest_cart.items():
                    items.append({
                        "key": key,
                        "producto_id": valor["producto_id"],
                        "cantidad": valor["cantidad"]
                    })
            
            # Actualizar la cantidad del item especificado
            if 0 <= item_index < len(items):
                item = items[item_index]
                nueva_cantidad = item["cantidad"] + change
                
                if nueva_cantidad < 1:
                    return JsonResponse({"success": False, "error": "La cantidad debe ser al menos 1"})
                
                if request.user.is_authenticated:
                    item_obj = item["object"]
                    talla_obj = item_obj.talla
                    if nueva_cantidad > talla_obj.stock:
                        return JsonResponse({"success": False, "error": "No hay suficiente stock"})
                    
                    item_obj.cantidad = nueva_cantidad
                    item_obj.save()
                else:
                    guest_cart = request.session.get("guest_cart", {})
                    key = item["key"]
                    if key in guest_cart:
                        talla_id = guest_cart[key]["talla_id"]
                        talla_obj = TallaProducto.objects.get(id=talla_id)
                        if nueva_cantidad > talla_obj.stock:
                            return JsonResponse({"success": False, "error": "No hay suficiente stock"})
                        
                        guest_cart[key]["cantidad"] = nueva_cantidad
                        request.session["guest_cart"] = guest_cart
                        request.session.modified = True
                
                return JsonResponse({"success": True})
        
        return JsonResponse({"success": False, "error": "Datos incompletos"})
    
    except json.JSONDecodeError:
        # Manejar solicitudes POST tradicionales (formulario)
        key = request.POST.get("key")
        nueva_cantidad = request.POST.get("cantidad")

        if not (key and nueva_cantidad):
            messages.error(request, "Datos incompletos para actualizar la cesta.")
            return redirect("detalles_cesta")

        try:
            nueva_cantidad = int(nueva_cantidad)
            if nueva_cantidad < 1:
                messages.error(request, "La cantidad debe ser al menos 1.")
                return redirect("detalles_cesta")
        except ValueError:
            messages.error(request, "Cantidad inválida.")
            return redirect("detalles_cesta")

        if request.user.is_authenticated:
            carrito = Carrito.objects.filter(cliente__usuario=request.user).first()
            if not carrito:
                messages.error(request, "No hay carrito activo.")
                return redirect("detalles_cesta")
            producto_id, talla, personalizacion_id = key.split("-")
            try:
                item = ItemCarrito.objects.get(carrito=carrito, producto_id=producto_id, talla=talla)
            except ItemCarrito.DoesNotExist:
                messages.error(request, "El producto no está en la cesta.")
                return redirect("detalles_cesta")

            talla_obj = TallaProducto.objects.get(id=item.talla.id)
            if nueva_cantidad > talla_obj.stock:
                messages.error(request, f"No hay suficiente stock para la talla {item.talla}")
                return redirect("detalles_cesta")

            item.cantidad = nueva_cantidad
            item.save()
        else:
            guest_cart = request.session.get("guest_cart", {})
            if key not in guest_cart:
                messages.error(request, "El producto no está en la cesta.")
                return redirect("detalles_cesta")

            talla_id = guest_cart[key]["talla_id"]
            talla_obj = TallaProducto.objects.get(id=talla_id)
            if nueva_cantidad > talla_obj.stock:
                messages.error(request, f"No hay suficiente stock para la talla {talla_obj.talla}")
                return redirect("detalles_cesta")

            guest_cart[key]["cantidad"] = nueva_cantidad
            request.session["guest_cart"] = guest_cart
            request.session.modified = True

        messages.success(request, "Cantidad actualizada correctamente.")
        return redirect("detalles_cesta")

def eliminar_producto_cesta(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"})

    # Manejar solicitudes JSON (AJAX)
    try:
        import json
        data = json.loads(request.body)
        item_index = data.get("item_index")
        
        if item_index is not None:
            # Obtener lista actual de items
            items = []
            keys = []
            
            if request.user.is_authenticated:
                carrito = Carrito.objects.filter(cliente__usuario=request.user).first()
                if carrito:
                    for item in carrito.items.all():
                        items.append({
                            "producto_id": item.producto.id,
                            "talla_id": item.talla.id,
                            "object": item
                        })
            else:
                guest_cart = request.session.get("guest_cart", {})
                for key in guest_cart.keys():
                    items.append({
                        "key": key
                    })
                    keys.append(key)
            
            # Eliminar el item especificado
            if 0 <= item_index < len(items):
                item = items[item_index]
                
                if request.user.is_authenticated:
                    item["object"].delete()
                else:
                    guest_cart = request.session.get("guest_cart", {})
                    key = keys[item_index]
                    if key in guest_cart:
                        del guest_cart[key]
                        request.session["guest_cart"] = guest_cart
                        request.session.modified = True
                
                return JsonResponse({"success": True})
        
        return JsonResponse({"success": False, "error": "Datos incompletos"})
    
    except json.JSONDecodeError:
        # Manejar solicitudes POST tradicionales (formulario)
        key = request.POST.get("key")

        if request.user.is_authenticated:
            carrito = Carrito.objects.filter(cliente__usuario=request.user).first()
            if carrito:
                producto_id, talla, personalizacion_id = key.split("-")
                ItemCarrito.objects.filter(carrito=carrito, producto_id=producto_id, talla=talla).delete()
        else:
            guest_cart = request.session.get("guest_cart", {})
            if key in guest_cart:
                del guest_cart[key]
                request.session["guest_cart"] = guest_cart
                request.session.modified = True

        messages.success(request, "Producto eliminado de la cesta.")
        return redirect("detalles_cesta")


def api_cart_data(request):
    """API endpoint para obtener los datos de la cesta en JSON"""
    items = []
    
    if request.user.is_authenticated:
        # Carrito del usuario registrado
        carrito = Carrito.objects.filter(cliente__usuario=request.user).first()
        if carrito:
            for item in carrito.items.all():
                items.append({
                    "nombre": item.producto.nombre,
                    "cantidad": item.cantidad,
                    "precio": f"{item.producto.precio:.2f}",
                    "subtotal": f"{item.producto.precio * item.cantidad:.2f}"
                })
    else:
        # Carrito de invitado en sesión
        carrito = request.session.get("guest_cart", {})
        for key, valor in carrito.items():
            producto_id = valor["producto_id"]
            cantidad = valor["cantidad"]
            try:
                producto = Producto.objects.get(id=producto_id)
                items.append({
                    "nombre": producto.nombre,
                    "cantidad": cantidad,
                    "precio": f"{producto.precio:.2f}",
                    "subtotal": f"{producto.precio * cantidad:.2f}"
                })
            except Producto.DoesNotExist:
                continue
    
    return JsonResponse({"items": items})


