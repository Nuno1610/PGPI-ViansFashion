// Función para obtener el token CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Función para actualizar la cesta flotante
function updateFloatingCart() {
    const cartIcon = document.querySelector('.cart-icon');
    const cartPreview = document.getElementById('cart-preview');
    const cartCount = document.getElementById('cart-count');
    const cartItemsPreview = document.getElementById('cart-items-preview');

    // Fetch cart data
    fetch(document.getElementById('api-cart-url').value)
        .then(response => response.json())
        .then(data => {
            const items = data.items || [];
            // Calcular el número total de productos (suma de cantidades)
            const totalProducts = items.reduce((sum, item) => sum + item.cantidad, 0);
            cartCount.textContent = totalProducts;

            if (items.length === 0) {
                cartItemsPreview.innerHTML = '<p class="empty-cart">Tu cesta está vacía</p>';
            } else {
                cartItemsPreview.innerHTML = items.map((item, index) => `
                    <div class="cart-item-preview">
                        <div class="cart-item-header">
                            <p class="cart-item-name">${item.nombre}</p>
                            <button class="delete-btn" onclick="deleteCartItem(${index})" title="Eliminar producto">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <polyline points="3 6 5 6 21 6"></polyline>
                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                    <line x1="10" y1="11" x2="10" y2="17"></line>
                                    <line x1="14" y1="11" x2="14" y2="17"></line>
                                </svg>
                            </button>
                        </div>
                        <p class="cart-item-details">${item.precio}€ x ${item.cantidad} = ${item.subtotal}€</p>
                        <div class="cart-item-controls">
                            <button class="quantity-btn" onclick="updateCartQuantity(${index}, -1)">−</button>
                            <span class="quantity-display">${item.cantidad}</span>
                            <button class="quantity-btn" onclick="updateCartQuantity(${index}, 1)">+</button>
                        </div>
                    </div>
                `).join('');
            }
        })
        .catch(error => console.error('Error fetching cart:', error));
}

// Función para actualizar la cantidad en la cesta
function updateCartQuantity(index, change) {
    fetch(document.getElementById('actualizar-cantidad-url').value, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            item_index: index,
            change: change
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateFloatingCart();
        }
    })
    .catch(error => console.error('Error updating quantity:', error));
}

// Función para eliminar un producto de la cesta
function deleteCartItem(index) {
    fetch(document.getElementById('eliminar-item-url').value, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            item_index: index
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateFloatingCart();
        }
    })
    .catch(error => console.error('Error deleting item:', error));
}

// Inicializar carrito flotante cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Solo mostrar carrito flotante en la página de catálogo
    const currentURL = window.location.pathname;
    const floatingCart = document.querySelector('.floating-cart');
    
    if (!currentURL.includes('/catalogo/') && currentURL !== '/catalogo') {
        floatingCart.style.display = 'none';
    } else {
        // Toggle cart preview
        const cartIcon = document.querySelector('.cart-icon');
        if (cartIcon) {
            cartIcon.addEventListener('click', function(e) {
                e.preventDefault();
                const cartPreview = document.getElementById('cart-preview');
                cartPreview.classList.toggle('show');
                updateFloatingCart();
            });
        }

        // Close cart when clicking outside
        document.addEventListener('click', function(e) {
            const cart = document.querySelector('.floating-cart');
            const cartPreview = document.getElementById('cart-preview');
            if (cart && !cart.contains(e.target) && cartPreview.classList.contains('show')) {
                cartPreview.classList.remove('show');
            }
        });

        // Update cart on page load
        updateFloatingCart();
    }
});
