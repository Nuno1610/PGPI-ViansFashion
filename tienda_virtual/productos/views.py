from io import BytesIO
from uuid import uuid4
from PIL import Image, ImageDraw, ImageFont

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db.models import Q, Min, Max
from django.urls import reverse
from django.core.files.base import ContentFile
from .models import Producto, Categoria, TallaProducto, ProductoPersonalizable, ImagenProducto, Marca
from .forms import PersonalizacionUsuarioForm, CategoriaForm, ProductoForm, ImagenProductoForm, TallaProductoForm, BaseImagenFormSet, BaseTallaFormSet, MarcaForm
from django.forms import inlineformset_factory

# -----------------------------------------------------------------------------
#  1. Funciones Auxiliares (Generación de Imágenes)
# -----------------------------------------------------------------------------

def generar_preview(imagen_base, texto, color_texto, imagen_extra=None,
                     texto_pos=None, imagen_pos=None, max_size=(400, 400), preview_size=None):
    try:
        # Abrir la imagen base y convertir a RGBA
        base = Image.open(imagen_base).convert("RGBA")
        base.thumbnail(max_size)
        width, height = base.size

        # Calcular factor de escala si tenemos el tamaño del preview
        if preview_size:
            scale_x = width / preview_size[0]
            scale_y = height / preview_size[1]
            print(f"Factor de escala X: {scale_x}, Y: {scale_y}")
        else:
            scale_x = scale_y = 1.0
            print(f"Sin preview_size, usando escala 1.0")
        
        # Imagen extra
        if imagen_extra:
            extra = Image.open(imagen_extra).convert("RGBA")
            
            max_extra_size = (int(width * 0.3), int(height * 0.3))
            extra.thumbnail(max_extra_size)
            extra_w, extra_h = extra.size
            
            if imagen_pos:
                # Aplicar factor de escala
                x_offset = imagen_pos[0] * scale_x - 9
                y_offset = imagen_pos[1] * scale_y - 9
            else:
                x_offset = (width - extra_w) / 2
                y_offset = height * 0.25
            
            x_offset = min(max(x_offset, 0), width - extra_w)
            y_offset = min(max(y_offset, 0), height - extra_h)
            
            base.paste(extra, (int(x_offset), int(y_offset)), extra)
        
        # Crear una capa nueva para el texto
        text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        
        try:
            font = ImageFont.truetype("arial.ttf", int(height * 0.1))
        except IOError:
            font = ImageFont.load_default()
        
        if texto:
            bbox = draw.textbbox((0, 0), texto, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            if texto_pos:
                # Aplicar factor de escala
                x_pos = texto_pos[0] * scale_x - 4
                y_pos = texto_pos[1] * scale_y + 4
                print(f"Posición texto calculada: ({x_pos}, {y_pos})")
            else:
                x_pos = (width - text_width) / 2
                y_pos = height * 0.60
            
            x_pos = min(max(x_pos, 0), width - text_width)
            y_pos = min(max(y_pos, 0), height - text_height)

            texto = texto.replace('\r\n', '\n').replace('\r', '\n')
            draw.multiline_text((x_pos, y_pos), texto, fill=color_texto, font=font, align="center")
        
        base.paste(text_layer, (0, 0), text_layer)
        
        buffer = BytesIO()
        base.save(buffer, format="PNG")
        return ContentFile(buffer.getvalue())
        
    except Exception as e:
        print(f"Error generando preview: {e}")
        try:
            with open(imagen_base.path, "rb") as f:
                return ContentFile(f.read())
        except Exception as e2:
            print(f"Error fallback preview: {e2}")
            return None

# -----------------------------------------------------------------------------
#  2. Vistas Principales
# -----------------------------------------------------------------------------

def catalogo(request, categoria_slug=None):
    categorias = Categoria.objects.all()
    marcas = Marca.objects.all()
    productos = Producto.objects.all().prefetch_related("tallas")

    # Filtrado por categoría
    categoria_actual = None
    if categoria_slug:
        categoria_actual = get_object_or_404(Categoria, slug=categoria_slug)
        productos = productos.filter(categoria=categoria_actual, es_visible=True)
    else:
        # Solo mostrar productos visibles en el catálogo general
        productos = productos.filter(es_visible=True)

    # Búsqueda por nombre, género y rango de precio
    # nombre: búsqueda por nombre o descripción (icontains)
    nombre = request.GET.get('nombre', '').strip()
    if nombre:
        productos = productos.filter(Q(nombre__icontains=nombre) | Q(descripcion__icontains=nombre))

    # genero: 'H', 'M', 'U', 'K' (si viene)
    genero = request.GET.get('genero', '').strip()
    if genero:
        productos = productos.filter(genero=genero)

    # marca: filtrar por ID de marca
    marca_id = request.GET.get('marca', '').strip()
    marca_seleccionada = None
    if marca_id:
        try:
            marca_id_int = int(marca_id)
            marca_seleccionada = Marca.objects.filter(id=marca_id_int).first()
            if marca_seleccionada:
                productos = productos.filter(marca=marca_seleccionada)
        except ValueError:
            # Si no es un número válido, ignorar el filtro
            pass

    # precio mínimo / precio máximo: filtrar por rango de precio
    precio_min = request.GET.get('precio_min', '').strip()
    precio_max = request.GET.get('precio_max', '').strip()
    precio_val_min = None
    precio_val_max = None
    try:
        from decimal import Decimal
        if precio_min:
            precio_val_min = Decimal(precio_min)
        if precio_max:
            precio_val_max = Decimal(precio_max)

        # Rechazar precios negativos
        if precio_val_min is not None and precio_val_min < 0:
            messages.error(request, "El precio mínimo no puede ser negativo.")
            precio_val_min = None
        if precio_val_max is not None and precio_val_max < 0:
            messages.error(request, "El precio máximo no puede ser negativo.")
            precio_val_max = None

        # Si tanto min como max tienen algún valor, validar que min <= max
        if precio_val_min is not None and precio_val_max is not None:
            if precio_val_min > precio_val_max:
                messages.error(request, "El precio mínimo no puede ser mayor que el precio máximo.")
            else:
                productos = productos.filter(precio__gte=precio_val_min, precio__lte=precio_val_max)
        else:
            if precio_val_min is not None:
                productos = productos.filter(precio__gte=precio_val_min)
            if precio_val_max is not None:
                productos = productos.filter(precio__lte=precio_val_max)
    except Exception:
        # Si la conversión falla, ignoramos el filtro de precios
        pass

    # Datos ficticios para mostrar la tarjeta de personalización en el HTML
    producto_personalizable = {
        "nombre": "Personaliza tu prenda",
        "imagen": "custom/custom.png",
        "precio": None,
        "custom": True
    }

    # Rango global de precios (para el slider). Usamos productos visibles.
    bounds = Producto.objects.filter(es_visible=True).aggregate(min_precio=Min('precio'), max_precio=Max('precio'))
    precio_bound_min = bounds.get('min_precio') or 0
    precio_bound_max = bounds.get('max_precio') or 0

    context = {
        "categorias": categorias,
        "categoria_actual": categoria_actual,
        "marcas": marcas,
        "productos": productos,
        "producto_personalizable": producto_personalizable,
        # Valores para rellenar el formulario de búsqueda
        "search_nombre": nombre,
        "search_genero": genero,
        "search_marca": marca_id,
        "marca_seleccionada": marca_seleccionada,
        "search_precio_min": precio_min,
        "search_precio_max": precio_max,
        "precio_bound_min": precio_bound_min,
        "precio_bound_max": precio_bound_max,
    }

    return render(request, "productos/catalogo.html", context)


def detalle_producto(request, id):
    producto = get_object_or_404(Producto, id=id)

    try:
        producto_personalizable = producto.productopersonalizable
        return redirect("personalizar_producto", producto_id=producto_personalizable.id)
    except ProductoPersonalizable.DoesNotExist:
        # Producto normal
        return render(request, "productos/detalle_producto.html", {
            "producto": producto,
            "imagenes": producto.imagenes.all(),
            "tallas": producto.tallas.all(),
        })


def personalizar_producto(request, producto_id):
    producto_base = get_object_or_404(ProductoPersonalizable, id=producto_id)

    if request.method == "POST":
        form = PersonalizacionUsuarioForm(producto=producto_base, data=request.POST, files=request.FILES)

        if form.is_valid():
            texto = form.cleaned_data.get("texto")
            color_texto = form.cleaned_data.get("color_texto")
            imagen_extra = form.cleaned_data.get("imagen")
            color = form.cleaned_data.get("color_producto")
            texto_x = request.POST.get("texto_x")
            texto_y = request.POST.get("texto_y")
            imagen_x = request.POST.get("imagen_x")
            imagen_y = request.POST.get("imagen_y")

            # Crear instancia de la personalización del usuario
            nueva_personalizacion = form.save(commit=False)
            nueva_personalizacion.usuario = request.user if request.user.is_authenticated else None
            nueva_personalizacion.producto_base = producto_base
            
            # Generar la preview
            imagen_base_obj = producto_base.imagenes.filter(color=color).first()
            if imagen_base_obj:
                imagen_base = imagen_base_obj.imagen
            else:
                # fallback: usar la imagen principal
                imagen_base = producto_base.imagen_principal
            
            preview_width = request.POST.get('preview_width')
            preview_height = request.POST.get('preview_height')
            preview_file = generar_preview(
                imagen_base=imagen_base,
                texto=texto,
                color_texto=color_texto,
                imagen_extra=imagen_extra,
                texto_pos=(float(texto_x), float(texto_y)) if texto_x and texto_y else None,
                imagen_pos=(float(imagen_x), float(imagen_y)) if imagen_x and imagen_y else None,
                preview_size=(int(preview_width), int(preview_height)) if preview_width and preview_height else None
            )

            if preview_file:
                nombre_preview = f"preview_{uuid4().hex}.png"
                nueva_personalizacion.imagen_generada.save(nombre_preview, preview_file, save=False)

            # Guardar la personalización
            nueva_personalizacion.save()

            # Redirigir al carrito, pasando la personalización
            talla_id = request.POST.get("talla")
            if not talla_id:
                messages.error("Debe seleccionar una talla")

            url = reverse("agregar_producto_cesta", args=[producto_base.id])
            url += f"?personalizacion_id={nueva_personalizacion.id}&talla={talla_id}"
            return redirect(url)

    else:
        form = PersonalizacionUsuarioForm(producto=producto_base)

    return render(request, "productos/personalizar_producto.html", {
        "producto": producto_base,
        "form": form,
    })

def producto_personalizado_preview(request, pk):
    producto_personalizado = get_object_or_404(ProductoPersonalizable, pk=pk)
    return render(request, 'productos/preview.html', {
        'producto_personalizado': producto_personalizado
    })


# -----------------------------------------------------------------------------
#  3. Vistas de Administración (Decoradores y acciones)
# -----------------------------------------------------------------------------

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)

@admin_required
def reponer_stock(request, id):
    if request.method != "POST":
        return redirect('detalle_producto', id=id)

    producto = get_object_or_404(Producto, id=id)
    talla_id = request.POST.get("talla_id")
    cantidad_str = request.POST.get("cantidad", "0")
    
    try:
        cantidad = int(cantidad_str)
    except ValueError:
        cantidad = 0

    talla = get_object_or_404(TallaProducto, id=talla_id, producto=producto)

    if cantidad <= 0:
        messages.error(request, "Cantidad inválida para reponer.")
        return redirect('detalle_producto', id=id)

    talla.stock += cantidad
    talla.save()

    messages.success(request, f"Se repusieron {cantidad} unidades de {producto.nombre} (Talla {talla.talla}).")
    return redirect('detalle_producto', id=id)

@admin_required
def eliminar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    producto.delete()
    messages.success(request, f"{producto.nombre} eliminado.")
    return redirect('catalogo')

@admin_required
def crear_categoria(request):
    if request.method == "POST":
        form = CategoriaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría creada correctamente.")
            return redirect('catalogo')
    else:
        form = CategoriaForm()
    return render(request, 'productos/admin_categoria_form.html', {'form': form, 'accion': 'Crear'})

@admin_required
def editar_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    if request.method == "POST":
        form = CategoriaForm(request.POST, request.FILES, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría actualizada correctamente.")
            return redirect('catalogo')
    else:
        form = CategoriaForm(instance=categoria)
    return render(request, 'productos/admin_categoria_form.html', {'form': form, 'accion': 'Editar'})

@admin_required
def eliminar_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    categoria.delete()
    messages.success(request, "Categoría eliminada correctamente.")
    return redirect('catalogo')


@admin_required
def crear_producto(request):
    ImagenFormSet = inlineformset_factory(
        Producto,ImagenProducto, form=ImagenProductoForm, extra=0, formset=BaseTallaFormSet,can_delete=True
    )
    TallaFormSet = inlineformset_factory(
        Producto,TallaProducto, form=TallaProductoForm, extra=0, formset=BaseTallaFormSet,can_delete=True
    )

    if request.method == "POST":
        form_producto = ProductoForm(request.POST)
        imagen_formset = ImagenFormSet(request.POST, request.FILES, queryset=ImagenProducto.objects.none(), prefix="imagen")
        talla_formset = TallaFormSet(request.POST, queryset=TallaProducto.objects.none(), prefix="talla")

        if form_producto.is_valid() and imagen_formset.is_valid() and talla_formset.is_valid():
            es_personalizable = request.POST.get('es_personalizable') == 'on'

            # Guardar producto o personalizable
            if es_personalizable:
                producto_base = form_producto.save(commit=False)
                producto = ProductoPersonalizable.objects.create(
                    nombre=producto_base.nombre,
                    descripcion=producto_base.descripcion,
                    precio=producto_base.precio,
                    marca=producto_base.marca,
                    categoria=producto_base.categoria,
                    genero=producto_base.genero,
                    color=producto_base.color,
                    material=producto_base.material,
                    es_destacado=producto_base.es_destacado,
                    es_visible=producto_base.es_visible,
                )
            else:
                producto = form_producto.save()

            # Guardar imágenes
            principal_marcada = False
            for form in imagen_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    es_principal = form.cleaned_data.get('es_principal', False)
                    # Solo una puede ser principal
                    if es_principal and not principal_marcada:
                        principal_marcada = True
                    else:
                        es_principal = False
                    ImagenProducto.objects.create(
                        producto=producto,
                        imagen=form.cleaned_data['imagen'],
                        color=form.cleaned_data.get('color', 'default'),
                        es_principal=es_principal
                    )

            # Si ninguna imagen se marcó como principal, marcamos la primera
            if not principal_marcada and producto.imagenes.exists():
                primera = producto.imagenes.first()
                primera.es_principal = True
                primera.save()

            # Guardar tallas
            for form in talla_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    TallaProducto.objects.create(
                        producto=producto,
                        talla=form.cleaned_data['talla'],
                        stock=form.cleaned_data['stock']
                    )

            messages.success(request, f"Producto '{producto.nombre}' creado correctamente.")
            return redirect('catalogo')
        else:
            messages.error(request, "Debes completar todos los campos correctamente.")

    else:
        form_producto = ProductoForm()
        imagen_formset = ImagenFormSet(queryset=ImagenProducto.objects.none(), prefix="imagen")
        talla_formset = TallaFormSet(queryset=TallaProducto.objects.none(), prefix="talla")

    return render(request, "productos/admin_producto_form.html", {
        'form': form_producto,
        'imagen_formset': imagen_formset,
        'talla_formset': talla_formset,
        'accion': 'Crear'
    })


@admin_required
def editar_producto_admin(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    
    ImagenFormSet = inlineformset_factory(
        Producto,ImagenProducto, form=ImagenProductoForm, extra=0, formset=BaseImagenFormSet, can_delete=True
    )
    TallaFormSet = inlineformset_factory(
        Producto,TallaProducto, form=TallaProductoForm, extra=0,formset=BaseTallaFormSet, can_delete=True
    )
    
    if request.method == "POST":
        form_producto = ProductoForm(request.POST, instance=producto)
        imagen_formset = ImagenFormSet(request.POST, request.FILES, instance=producto, prefix="imagen")
        talla_formset = TallaFormSet(request.POST, instance=producto, prefix="talla")
        
        if form_producto.is_valid() and imagen_formset.is_valid() and talla_formset.is_valid():
            # Guardar producto
            producto_actualizado = form_producto.save()
            
            # Guardar imágenes
            imagenes = imagen_formset.save(commit=False)
            for imagen in imagenes:
                imagen.producto = producto_actualizado
                imagen.save()
            
            # Eliminar imágenes marcadas para borrar
            for obj in imagen_formset.deleted_objects:
                obj.delete()
            
            # Verificar que haya al menos una imagen principal
            if not producto_actualizado.imagenes.filter(es_principal=True).exists():
                if producto_actualizado.imagenes.exists():
                    primera = producto_actualizado.imagenes.first()
                    primera.es_principal = True
                    primera.save()
            
            # Guardar tallas
            tallas = talla_formset.save(commit=False)
            for talla in tallas:
                talla.producto = producto_actualizado
                talla.save()
            
            # Eliminar tallas marcadas para borrar
            for obj in talla_formset.deleted_objects:
                obj.delete()
            
            messages.success(request, f"Producto '{producto_actualizado.nombre}' actualizado correctamente.")
            return redirect('detalle_producto', id=producto.id)
        else:
            messages.error(request, "Debes completar todos los campos correctamente.")
    
    else:
        form_producto = ProductoForm(instance=producto)
        imagen_formset = ImagenFormSet(instance=producto, prefix="imagen")
        talla_formset = TallaFormSet(instance=producto, prefix="talla")
    
    return render(request, "productos/admin_producto_editar.html", {
        'form': form_producto,
        'imagen_formset': imagen_formset,
        'talla_formset': talla_formset,
        'producto': producto,
    })

@admin_required
def agregar_imagen_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == "POST":
        imagen = request.FILES.get("imagen")
        es_principal = request.POST.get("es_principal") == "on"
        color = request.POST.get("color", "default")

        if not imagen:
            messages.error(request, "Debes seleccionar una imagen.")
            return redirect('editar_producto_admin', id=producto.id)

        # Si se marca como principal, quitar la principal anterior
        if es_principal:
            producto.imagenes.update(es_principal=False)

        nueva_imagen = ImagenProducto.objects.create(
            producto=producto,
            imagen=imagen,
            es_principal=es_principal,
            color=color
        )
        messages.success(request, f"Imagen agregada al producto {producto.nombre}.")
        return redirect('editar_producto_admin', id=producto.id)

    return render(request, 'productos/admin_agregar_imagen.html', {'producto': producto})

@admin_required
def agregar_talla_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == "POST":
        talla = request.POST.get("talla", "").strip()
        stock_str = request.POST.get("stock", "0").strip()

        if not talla:
            messages.error(request, "Debes indicar la talla.")
            return redirect('editar_producto_admin', id=producto.id)

        try:
            stock = int(stock_str)
            if stock < 0:
                raise ValueError()
        except ValueError:
            messages.error(request, "El stock debe ser un número entero positivo.")
            return redirect('editar_producto_admin', id=producto.id)

        # Evitar duplicados
        obj, created = TallaProducto.objects.get_or_create(producto=producto, talla=talla)
        if not created:
            obj.stock += stock
            obj.save()
            messages.success(request, f"Se actualizó el stock de la talla {talla} ({obj.stock} unidades).")
        else:
            obj.stock = stock
            obj.save()
            messages.success(request, f"Talla {talla} agregada con {stock} unidades.")

        return redirect('editar_producto_admin', id=producto.id)

    return render(request, 'productos/admin_agregar_talla.html', {'producto': producto})

@admin_required
def crear_marca(request):
    """Vista para crear una nueva marca"""
    if request.method == "POST":
        form = MarcaForm(request.POST, request.FILES)
        if form.is_valid():
            marca = form.save()
            messages.success(request, f"Marca '{marca.nombre}' creada correctamente.")
            return redirect('catalogo')
        else:
            messages.error(request, "Por favor, corrige los errores del formulario.")
    else:
        form = MarcaForm()
    
    return render(request, 'productos/admin_marca_form.html', {
        'form': form,
        'accion': 'Crear'
    })


@admin_required
def editar_marca(request, marca_id):
    """Vista para editar una marca existente"""
    marca = get_object_or_404(Marca, id=marca_id)
    
    if request.method == "POST":
        form = MarcaForm(request.POST, request.FILES, instance=marca)
        if form.is_valid():
            marca_actualizada = form.save()
            messages.success(request, f"Marca '{marca_actualizada.nombre}' actualizada correctamente.")
            return redirect('catalogo')
        else:
            messages.error(request, "Por favor, corrige los errores del formulario.")
    else:
        form = MarcaForm(instance=marca)
    
    return render(request, 'productos/admin_marca_form.html', {
        'form': form,
        'marca': marca,
        'accion': 'Editar'
    })


@admin_required
def eliminar_marca(request, marca_id):
    """Vista para eliminar una marca"""
    marca = get_object_or_404(Marca, id=marca_id)
    
    # Verificar si hay productos usando esta marca
    productos_con_marca = Producto.objects.filter(marca=marca).count()
    
    if productos_con_marca > 0:
        messages.error(
            request, 
            f"No se puede eliminar la marca '{marca.nombre}' porque tiene {productos_con_marca} producto(s) asociado(s). "
            f"Primero debes eliminar o reasignar esos productos."
        )
        return redirect('catalogo')
    
    nombre_marca = marca.nombre
    marca.delete()
    messages.success(request, f"Marca '{nombre_marca}' eliminada correctamente.")
    return redirect('catalogo')