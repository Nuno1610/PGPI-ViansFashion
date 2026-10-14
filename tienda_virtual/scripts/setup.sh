#!/bin/bash

# Detener el script si ocurre cualquier error
set -e

# Función para manejar errores
handle_error() {
    echo "ERROR DURANTE EL SETUP"
    exit 1
}

# Atrapamos cualquier señal de error (exit code != 0)
trap 'handle_error' ERR

# Obtener la ruta del script actual
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/.."
ROOT_DIR="$SRC_DIR/.."

echo "Creando entorno virtual en la raíz..."
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD=python3.12
else
    echo "Python 3.12 no encontrado, usando python3..."
    PYTHON_CMD=python3
fi

$PYTHON_CMD -m venv "$ROOT_DIR/.venv"

echo "Activando entorno virtual..."
source "$ROOT_DIR/.venv/bin/activate"

echo "Instalando dependencias desde src/requirements.txt..."
python -m pip install --upgrade pip
python -m pip install -r "$SRC_DIR/requirements.txt"

echo "Ejecutando migraciones..."
python "$SRC_DIR/manage.py" migrate

echo "Generando datos de prueba..."
python "$SRC_DIR/manage.py" runscript crear_datos_prueba

echo "PROCESO COMPLETADO CORRECTAMENTE"