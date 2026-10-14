from django.shortcuts import render, get_object_or_404, redirect
from pedidos.models import Pedido, ItemPedido
from cesta.models import Carrito
from productos.models import Producto, TallaProducto, PersonalizacionUsuario
from usuarios.models import Cliente
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Case, When, Value, IntegerField
from django.contrib import messages
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from django.conf import settings
import stripe
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from io import BytesIO
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.core.paginator import Paginator



stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def listar_pedidos(request):
    # Anotamos prioridad: 0 para pedidos en revisión, 1 para el resto
    pedidos = Pedido.objects.annotate(
        prioridad=Case(
            When(estado='ENRV', then=Value(0)),
            default=Value(1),
            output_field=IntegerField()
        )
    ).order_by('prioridad', '-fecha_creacion') 

    return render(request, 'pedidos/listar_pedidos_admin.html', {'pedidos': pedidos})

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)

@admin_required
def cancelar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Solo permitir cancelar si está en revisión
    if pedido.estado == 'ENRV':
        pedido.estado = 'CANC'
        pedido.save()
        messages.success(request, f"Pedido {pedido.numero_pedido} cancelado correctamente.")
    
    return redirect('listar_pedidos')

@admin_required
def aceptar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Solo permitir aceptar si está en revisión
    if pedido.estado == 'ENRV':
        pedido.estado = 'PROC'
        pedido.save()
        messages.success(request, f"Pedido {pedido.numero_pedido} aceptado correctamente.")
    
    return redirect('listar_pedidos')

def checkout(request):

    # USUARIO REGISTRADO
    if request.user.is_authenticated:
        carrito = Carrito.objects.filter(cliente__usuario=request.user).first()

        if not carrito or carrito.items.count() == 0:
            return redirect("detalles_cesta")

        items = []

        for item in carrito.items.all():
            items.append({
                "producto": item.producto,
                "nombre": item.producto.nombre,
                "talla": item.talla,
                "cantidad": item.cantidad,
                "subtotal": item.producto.precio * item.cantidad
            })

        total = sum(i["subtotal"] for i in items)

    # USUARIO SIN REGISTRAR
    else:
        guest_cart = request.session.get("guest_cart", {})

        if not guest_cart:
            return redirect("detalles_cesta")

        items = []
        total = 0

        for key, data in guest_cart.items():
            try:
                producto_id, talla_id, personalizacion_id = key.split("-")
                producto = Producto.objects.get(id=int(producto_id))
                talla_obj = TallaProducto.objects.get(id=int(talla_id))
            except (Producto.DoesNotExist, TallaProducto.DoesNotExist, ValueError):
                continue

            cantidad = data.get("cantidad", 1)
            subtotal = producto.precio * cantidad

            total += subtotal

            items.append({
                "producto": producto,
                "nombre": producto.nombre,
                "talla": talla_obj.talla,
                "cantidad": cantidad,
                "subtotal": subtotal
            })

    # Render del checkout
    return render(request, "pedidos/checkout.html", {
        "items": items,
        "total": total,
    })


def crear_pedido(request):
    # GET: mostrar formulario de envío y resumen
    if request.method == "GET":
        if request.user.is_authenticated:
            cliente = Cliente.objects.get(usuario=request.user)
            carrito = Carrito.objects.filter(cliente=cliente).first()
            items = []
            total = 0
            if carrito:
                for item in carrito.items.all():
                    subtotal = item.producto.precio * item.cantidad
                    total += subtotal
                    items.append({
                        "producto": item.producto,
                        "nombre": item.producto.nombre,
                        "talla": item.talla,
                        "cantidad": item.cantidad,
                        "subtotal": subtotal
                    })
        else:
            guest_cart = request.session.get("guest_cart", {})
            items = []
            total = 0
            for key, data in guest_cart.items():
                try:
                    producto_id, talla_id, personalizacion_id = key.split("-")
                    producto = Producto.objects.get(id=int(producto_id))
                    talla_obj = TallaProducto.objects.get(id=int(talla_id))
                except:
                    continue
                cantidad = data.get("cantidad", 1)
                subtotal = producto.precio * cantidad
                total += subtotal
                items.append({
                    "producto": producto,
                    "nombre": producto.nombre,
                    "talla": talla_obj.talla,
                    "cantidad": cantidad,
                    "subtotal": subtotal
                })

        return render(request, "pedidos/checkout.html", {
            "show_payment": False,
            "items": items,
            "total": total
        })

    # POST: crear pedido y PaymentIntent
    # Obtener items del carrito
    if request.user.is_authenticated:
        cliente = Cliente.objects.get(usuario=request.user)
        carrito = Carrito.objects.filter(cliente=cliente).first()
        items_origen = carrito.items.all()
    else:
        cliente = None
        carrito = None
        items_origen = request.session.get("guest_cart", {})
    
    nombre_cliente = request.POST.get("nombre")
    email = request.POST.get("email")
    telefono = request.POST.get("telefono")
    cp = request.POST.get("cp", "").strip()

    # Validación del lado servidor: teléfono debe ser 9 dígitos, CP 5 dígitos
    if not telefono or not telefono.isdigit() or len(telefono) != 9:
        messages.error(request, "El teléfono debe contener exactamente 9 dígitos.")
        return redirect('crear_pedido')

    if not cp or not cp.isdigit() or len(cp) != 5:
        messages.error(request, "El código postal debe contener exactamente 5 dígitos.")
        return redirect('crear_pedido')

    if not items_origen:
        return redirect("detalles_cesta")

    # Calcular total
    total = 0
    if request.user.is_authenticated:
        for item in items_origen:
            total += item.producto.precio * item.cantidad
    else:
        for key, data in items_origen.items():
            try:
                producto_id, talla_id, personalizacion_id = key.split("-")
                producto = Producto.objects.get(id=int(producto_id))
            except:
                continue
            total += producto.precio * data.get("cantidad",1)

    # Crear Pedido
    pedido = Pedido.objects.create(
        cliente=cliente,
        nombre_cliente=nombre_cliente,
        email=email,
        numero_pedido=f"VFF-{Pedido.objects.count()+1:06d}",
        estado="ENRV",
        metodo_pago="stripe",
        direccion_envio=request.POST.get("direccion"),
        telefono=telefono
    )

    # Crear items del pedido
    if request.user.is_authenticated:
        for item in items_origen:
            ItemPedido.objects.create(
                pedido=pedido,
                producto=item.producto,
                talla=item.talla.talla,
                cantidad=item.cantidad,
                precio_unitario=item.producto.precio,
                personalizacion=item.personalizacion
            )
    else:
        for key, data in items_origen.items():
            try:
                producto_id, talla_id, personalizacion_id = key.split("-")
                producto = Producto.objects.get(id=int(producto_id))
                talla_obj = TallaProducto.objects.get(id=int(talla_id))
                personalizacion = None
                if personalizacion_id != "None":
                    personalizacion = PersonalizacionUsuario.objects.get(id=int(personalizacion_id))
            except:
                continue
            
            ItemPedido.objects.create(
                pedido=pedido,
                producto=producto,
                talla=talla_obj.talla,
                cantidad=data.get("cantidad",1),
                precio_unitario=producto.precio,
                personalizacion=personalizacion
            )

    # Crear PaymentIntent en Stripe
    intent = stripe.PaymentIntent.create(
        amount=int(total*100), 
        currency="eur",
        metadata={"numero_pedido": pedido.numero_pedido}
    )
    pedido.stripe_payment_intent = intent.id
    pedido.save()

    # Renderizar checkout con Stripe
    return render(request, "pedidos/checkout.html", {
        "show_payment": True,
        "pedido": pedido,
        "client_secret": intent.client_secret,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
        "success_url": request.build_absolute_uri(
            f"/pedidos/completado/{pedido.numero_pedido}/"
        )
    })

def pedido_completado(request, numero_pedido):
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido)
    items = pedido.items.all()

    if pedido.stripe_payment_intent:
        intent = stripe.PaymentIntent.retrieve(pedido.stripe_payment_intent)

        # Solo si el pago está confirmado
        if intent.status == "succeeded" and not pedido.pago_completado:
            pedido.estado = "ENRV"
            pedido.pago_completado = True
            pedido.save()

            # 2. Enviar factura solo una vez
            enviar_factura_por_email(pedido, pedido.items.all())

    # Usuario registrado
    if pedido.cliente:
        carrito = Carrito.objects.filter(cliente=pedido.cliente).first()
        if carrito:
            carrito.items.all().delete()
    # Usuario anónimo
    else:
        request.session['guest_cart'] = {}
        request.session.modified = True

    return render(request, "pedidos/pedido_completado.html", {
        "pedido": pedido,
        "items": items
    })

def generar_factura_pdf(pedido, items):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ---------------- Título ----------------
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height-130, f"Factura de tu compra #{pedido.numero_pedido}")

    # ---------------- Datos del cliente ----------------
    styles = getSampleStyleSheet()
    y_cliente = height-170
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_cliente, "Datos del cliente:")
    c.setFont("Helvetica", 11)
    y_cliente -= 20
    c.drawString(60, y_cliente, f"Nombre: {pedido.nombre_cliente}")
    y_cliente -= 15
    c.drawString(60, y_cliente, f"Email: {pedido.email}")
    y_cliente -= 15
    c.drawString(60, y_cliente, f"Dirección: {pedido.direccion_envio}")
    y_cliente -= 15
    c.drawString(60, y_cliente, f"Teléfono: {pedido.telefono}")
    y_cliente -= 15
    c.drawString(60, y_cliente, f"Fecha: {pedido.fecha_creacion}")

    # ---------------- Tabla de items ----------------
    y_tabla = y_cliente - 40
    data = [["Producto", "Cantidad", "Subtotal"]]
    for item in items:
        data.append([
            item.producto.nombre, 
            str(item.cantidad),  
            f"{item.total:.2f} €",
        ])

    data.append(["", "Total:", f"{pedido.total:.2f} €"])

    table = Table(data, colWidths=[250, 60, 80, 80])
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f2f2f2")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-2), 0.5, colors.grey),
        ('BACKGROUND', (-2,-1), (-1,-1), colors.HexColor("#d9edf7")),
        ('TEXTCOLOR', (-2,-1), (-1,-1), colors.black),
        ('ALIGN', (-2,-1), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (-2,-1), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
    ])
    table.setStyle(style)

    table.wrapOn(c, width, height)
    table.drawOn(c, 50, y_tabla - (len(data) * 20))

    # ---------------- Mensaje final ----------------
    c.setFont("Helvetica-Oblique", 11)
    y = 50
    c.drawString(50, y, "¡Gracias por confiar en Vians Fashion! Esperamos verte pronto.")
    y -= 15
    c.drawString(50, y, "Puedes contactarnos a través de esta dirección de correo: contacto@viansfashion.com")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def enviar_factura_por_email(pedido, items):
    pdf_buffer = generar_factura_pdf(pedido, items)

    subject = f"Factura de tu compra #{pedido.numero_pedido}"
    from_email = "viansfashionesp@gmail.com"
    to_email = [pedido.email]

    html_content = render_to_string("pedidos/factura.html", {
        "pedido": pedido,
        "items": items,
    })

    text_content = f"Hola {pedido.nombre_cliente}, gracias por tu compra. Adjuntamos la factura."

    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    email.attach(f"Factura-{pedido.numero_pedido}.pdf", pdf_buffer.getvalue(), "application/pdf")
    email.send(fail_silently=False)

# FUNCIÓN SEGUIMIENTO DE PEDIDOS
def mis_pedidos(request):
    if not request.user.is_authenticated:
        pedidos_usuario = Pedido.objects.none()
    else:
        pedidos_usuario = Pedido.objects.filter(cliente__usuario=request.user).order_by("-fecha_creacion")

    paginator = Paginator(pedidos_usuario, 5)  # 5 pedidos por página
    page = request.GET.get("page")
    pedidos = paginator.get_page(page)

    return render(request, "pedidos/mis_pedidos.html", {
        "pedidos": pedidos
    })

def detalle_pedido(request, numero_pedido):
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido, cliente__usuario=request.user)
    items = pedido.items.all()

    return render(request, "pedidos/detalle_pedido.html", {
        "pedido": pedido,
        "items": items,
    })

@admin_required
def detalle_pedido_admin(request, numero_pedido):
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido)
    items = pedido.items.all()

    return render(request, "pedidos/detalle_pedido.html", {
        "pedido": pedido,
        "items": items,
    })

@admin_required
def cambiar_estado_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    if request.method == "POST":
        nuevo_estado = request.POST.get("nuevo_estado")
        if nuevo_estado in dict(Pedido.ESTADOS).keys():
            pedido.estado = nuevo_estado
            pedido.save()
            messages.success(request, f"Estado del pedido {pedido.numero_pedido} actualizado correctamente.")
    
    return redirect('detalle_pedido_admin', numero_pedido=pedido.numero_pedido)

def seguimiento_pedido(request, numero_pedido):
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido)

    # Si el pedido tiene cliente asociado, sólo el propietario (o superuser) puede verlo
    if pedido.cliente is not None:
        # Si no está autenticado o no es el propietario, mostrar página de acceso denegado
        if not request.user.is_authenticated:
            return render(request, "pedidos/acceso_denegado.html", {
                "message": "No es posible acceder a ese pedido."
            })

        cliente_usuario = getattr(pedido.cliente, 'usuario', None)
        if cliente_usuario != request.user and not request.user.is_superuser:
            return render(request, "pedidos/acceso_denegado.html", {
                "message": "No es posible acceder a ese pedido."
            })

    items = pedido.items.all()

    return render(request, "pedidos/seguimiento_pedido.html", {
        "pedido": pedido,
        "items": items,
    })

def buscar_pedido_anonimo(request):
    """Vista para que usuarios no autenticados busquen su pedido por número."""
    pedido = None
    items = None
    error = None
    
    if request.method == "POST":
        numero_pedido = request.POST.get("numero_pedido", "").strip()
        
        if not numero_pedido:
            error = "Por favor, ingresa el número de pedido."
        else:
            # Buscar el pedido sin requerir autenticación
            pedido = Pedido.objects.filter(numero_pedido=numero_pedido).first()
            
            if not pedido:
                error = f"No se encontró ningún pedido con el número '{numero_pedido}'."
            else:
                items = pedido.items.all()
    
        # Si encontramos el pedido, decidir si mostrar detalle o denegar acceso
        if pedido:
            # Pedidos realizados como invitado: permitir ver detalle
            if pedido.cliente is None:
                return render(request, "pedidos/detalle_pedido.html", {
                    "pedido": pedido,
                    "items": items,
                })

            # Si el pedido tiene cliente, solo el propietario o superuser puede verlo
            cliente_usuario = getattr(pedido.cliente, 'usuario', None)
            if request.user.is_authenticated and (cliente_usuario == request.user or request.user.is_superuser):
                return render(request, "pedidos/detalle_pedido.html", {
                    "pedido": pedido,
                    "items": items,
                })
            else:
                return render(request, "pedidos/acceso_denegado.html", {
                    "message": "No es posible acceder a ese pedido."
                })

    return render(request, "pedidos/buscar_pedido_anonimo.html", {
        "pedido": pedido,
        "items": items,
        "error": error,
    })

