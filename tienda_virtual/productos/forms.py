from django import forms
from .models import PersonalizacionUsuario, Categoria, TallaProducto, Categoria, ImagenProducto, Producto, Marca
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet

class PersonalizacionUsuarioForm(forms.ModelForm):
    texto = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.Textarea(attrs={'maxlength': 30, 'placeholder': 'Escribe tu texto...', 'rows': 3,'style': 'resize: none;'})
    )
    color_texto = forms.CharField(widget=forms.TextInput(attrs={'type': 'color'}), required=False)
    imagen = forms.ImageField(required=False)
    cantidad = forms.IntegerField(
        min_value=1, 
        initial=1,
        widget=forms.NumberInput(attrs={'id': 'id_cantidad'})
    )
    color_producto = forms.ChoiceField(required=False, choices=[], widget=forms.Select(attrs={'id': 'id_color_producto'}))

    class Meta:
        model = PersonalizacionUsuario
        fields = ['texto', 'color_texto', 'imagen', 'cantidad', 'color_producto']

    def __init__(self, *args, **kwargs):
        producto = kwargs.pop('producto', None)
        self.producto = producto  # Guardar para usarlo en clean()
        super().__init__(*args, **kwargs)
        
        # Si se pasa el producto, rellenamos las opciones de color según las imágenes disponibles
        if producto:
            colores = [(img.color, img.color.capitalize()) for img in producto.imagenes.all() if img.color != "default"]
            if colores:
                self.fields['color_producto'].choices = colores
            else:
                self.fields['color_producto'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        cantidad = cleaned_data.get('cantidad')
        
        # Obtener talla_id del POST (viene del HTML)
        talla_id = self.data.get('talla')
        
        if talla_id and cantidad and self.producto:
            try:
                talla = TallaProducto.objects.get(id=talla_id, producto=self.producto)
                
                if cantidad > talla.stock:
                    raise forms.ValidationError(
                        'No hay suficiente stock disponible para esta talla.'
                    )
                if talla.stock == 0:
                    raise forms.ValidationError(
                        'Esta talla no tiene stock disponible.'
                    )
            except TallaProducto.DoesNotExist:
                raise forms.ValidationError('Talla no válida.')

        return cleaned_data

    def save(self, commit=True, autor=None):
        instance = super().save(commit=False)

        # Configuración básica
        instance.configuracion = {
            "texto": self.cleaned_data.get('texto'),
            "color_texto": self.cleaned_data.get('color_texto'),
            "color_producto": self.cleaned_data.get('color_producto'),
        }

        if autor:
            instance.autor = autor

        # La imagen no se guarda
        self._imagen_subida = self.cleaned_data.get('imagen')

        return instance
class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'precio', 'marca', 'categoria',
            'genero', 'material', 'es_destacado', 'es_visible',
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }

class ImagenProductoForm(forms.ModelForm):
    class Meta:
        model = ImagenProducto
        fields = ['imagen', 'es_principal', 'color']

class TallaProductoForm(forms.ModelForm):
    class Meta:
        model = TallaProducto
        fields = ['talla', 'stock']

class BaseImagenFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        count = 0
        principal_count = 0
        for form in self.forms:
            # ignorar los eliminados
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False):
                count += 1
                if form.cleaned_data.get('es_principal', False):
                    principal_count += 1

        if count < 1:
            raise ValidationError("Debe añadir al menos una.")
        if principal_count > 1:
            raise ValidationError("Solo puede haber una imagen principal.")
        
class BaseTallaFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        count = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False):
                count += 1

        if count < 1:
            raise ValidationError("Debe añadir al menos una.")


class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ['nombre', 'imagen']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Ej: Nike, Adidas, Puma...',
                'maxlength': 100
            }),
        }
        labels = {
            'nombre': 'Nombre de la marca',
            'imagen': 'Logo de la marca (opcional)',
        }