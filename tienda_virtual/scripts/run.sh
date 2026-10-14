#!/bin/bash

# Detener el script si ocurre un error
set -e

# --- Configuración de Rutas ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/.."
ROOT_DIR="$SRC_DIR/.."

# --- Verificación y Activación del Entorno ---
if [ ! -d "$ROOT_DIR/.venv" ]; then
    echo "Error: No se encontró el entorno virtual en $ROOT_DIR/.venv"
    echo "Por favor, ejecuta primero setup.sh"
    exit 1
fi

echo "Activando entorno virtual..."
source "$ROOT_DIR/.venv/bin/activate"

# --- Ejecución del Servidor ---
echo "Iniciando servidor Django..."
python "$SRC_DIR/manage.py" runserver "$@"