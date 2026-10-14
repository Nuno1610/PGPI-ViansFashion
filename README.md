# Vians fashion

**Descripción**
- Tienda virtual de ropa personalizable en Django preparada para desarrollo local, con módulos para `productos`, `cesta`, `pedidos`, `usuarios`, `home`, etc.

**Requisitos**
- Python 3.12 (recomendado). El proyecto puede funcionar con Python 3.10/3.11 en muchos casos, pero los scripts asumen 3.12.
- pip (gestor de paquetes de Python).

**Archivos importantes**
- `tienda_virtual/` : código Django (configuración, `manage.py`, settings).
- `tienda_virtual/scripts/` : scripts de ayuda para `setup`, `run` y `test_coverage` (tanto para Bash como para Windows).

- `db.sqlite3` : base de datos SQLite por defecto (útil para desarrollo).
- `media/` : carpeta donde se almacenan imágenes subidas (p. ej. `media/productos`).

### Paso previo a instalación:

**Configuración del archivo .env**

Antes de levantar la aplicación, cada persona debe crear su propio archivo `.env` local con las claves privadas de su entorno. El proyecto ya incluye una plantilla en `tienda_virtual/.env.example` para facilitarlo.

1. Entra en la carpeta del proyecto y copia la plantilla:

```bash
cp tienda_virtual/.env.example tienda_virtual/.env
```

En Windows PowerShell:

```powershell
Copy-Item tienda_virtual/.env.example tienda_virtual/.env
```

Si prefieres hacerlo desde la terminal de Windows con comandos de sistema, también puedes:

```powershell
copy tienda_virtual\.env.example tienda_virtual\.env
```

2. Edita el archivo `tienda_virtual/.env` con tus valores reales.

> Importante: el archivo `.env` local no se sube al repositorio. Solo debe quedar la plantilla `.env.example` en Git.

```env
SECRET_KEY='tu_clave_secreta_generada'
DEBUG=True
ALLOWED_HOSTS='localhost,127.0.0.1,0.0.0.0'

EMAIL_HOST='smtp.gmail.com'
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER='tu-email@gmail.com'
EMAIL_HOST_PASSWORD='tu_contraseña_de_aplicacion'
DEFAULT_FROM_EMAIL='tu-email@gmail.com'

STRIPE_PUBLIC_KEY='pk_test_tu_public_key'
STRIPE_SECRET_KEY='sk_test_tu_secret_key'
STRIPE_WEBHOOK_SECRET='whsec_tu_webhook_secret'
```

3. Configura los valores reales:

- `SECRET_KEY`: genera una clave aleatoria segura para Django.
- `DEBUG`: deja `True` en local y `False` en producción.
- `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD`: normalmente se usa un correo de Gmail con autenticación por contraseña de aplicación. Si usas Gmail, activa verificación en dos pasos y crea una contraseña de aplicación.
- `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY` y `STRIPE_WEBHOOK_SECRET`: deben obtenerse desde el panel de Stripe.

#### Cómo configurar Stripe

1. Accede a tu dashboard de Stripe.
2. En el menú de la izquierda entra en `Developers` > `API keys`.
3. Copia:
   - `Publishable key` → `STRIPE_PUBLIC_KEY`
   - `Secret key` → `STRIPE_SECRET_KEY`
4. Para los webhooks:
   - Ve a `Developers` > `Webhooks`
   - Añade un endpoint local o de pruebas
   - Copia el `Signing secret` y ponlo en `STRIPE_WEBHOOK_SECRET`

Importante: nunca compartas estas claves ni las subas al repositorio. El archivo `.env` está ignorado por Git para evitar filtraciones.

#### Cómo configurar el correo

Si usarás Gmail para notificaciones o recuperación de contraseña:

1. Activa la verificación en dos pasos en tu cuenta de Google.
2. Genera una `Contraseña de aplicación`.
3. Copia esa contraseña en `EMAIL_HOST_PASSWORD`.
4. Usa el correo completo en `EMAIL_HOST_USER`.

> El proyecto usa estas variables en `tienda_virtual/tienda_virtual/settings.py`, por lo que si no existen o están mal configuradas, algunas funciones como envío de correos o pagos con Stripe pueden fallar.

**Instalación (rápida)**

Recomendado: usar los scripts incluidos para crear el entorno virtual, instalar dependencias y generar datos de prueba.

- En Linux / macOS / WSL (Bash):

```bash

./tienda_virtual/scripts/setup.sh
```

El script hace lo siguiente:
- crea un entorno virtual `.venv` en la raíz del proyecto (usa `python3.12` o `python3` si no encuentra 3.12)
- activa el entorno

- instala dependencias desde `tienda_virtual/requirements.txt`
- ejecuta las migraciones y genera datos de prueba (`createsample` a través de `runscript crear_datos_prueba`).

- En Windows (PowerShell):

```powershell

.\tienda_virtual\scripts\setup.bat
```

El `setup.bat` realiza pasos equivalentes para Windows (crea `.venv`, instala dependencias y ejecuta migraciones y datos de prueba). El script intenta usar `py -3.12` para crear el venv.

Si prefieres hacerlo manualmente:

```bash

python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r tienda_virtual/requirements.txt

python tienda_virtual/manage.py migrate
python tienda_virtual/manage.py runscript crear_datos_prueba

```

o en PowerShell (manual):

```powershell
py -3.12 -m venv .\.venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r tienda_virtual\requirements.txt

python tienda_virtual/manage.py migrate
python tienda_virtual/manage.py runscript crear_datos_prueba

```

**Crear/Eliminar datos de prueba**

- Para generar datos de prueba (si no lo hizo `setup`):

```bash

python tienda_virtual/manage.py runscript crear_datos_prueba
```

- Para eliminar los datos de prueba creados por los scripts:

```bash

python tienda_virtual/manage.py runscript borrar_datos_prueba
```

Los scripts de datos (`crear_datos_prueba.py` y `borrar_datos_prueba.py`) usan prefijos `TEST_` y `test_` para facilitar su eliminación segura.

**Ejecutar el servidor (desarrollo)**
- Usando el script (Bash):

```bash

./tienda_virtual/scripts/run.sh
```

- Usando el script (Windows):

```powershell

.\tienda_virtual\scripts\run.bat
```

- O manualmente (desde la raíz del proyecto, con el entorno activado):

```bash

python tienda_virtual/manage.py runserver
```

**Crear superusuario (admin)**

```bash

python tienda_virtual/manage.py createsuperuser
```

**Tests y cobertura**
Hay scripts para ejecutar los tests con cobertura y generar un reporte HTML.

- Bash:

```bash

./tienda_virtual/scripts/test_coverage.sh            # Ejecuta todos los tests
./tienda_virtual/scripts/test_coverage.sh productos  # Ejecuta tests del módulo 'productos'
```

- Windows:

```powershell

.\tienda_virtual\scripts\test_coverage.bat
.\tienda_virtual\scripts\test_coverage.bat productos
```

Los scripts generan `htmlcov/index.html` con el reporte de cobertura.

**Base de datos y medios**
- El proyecto utiliza `db.sqlite3` por defecto.
- Las imágenes de productos se esperan en `media/productos`.

**Autores**
- Grupo PGPI G1.17

---
