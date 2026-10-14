#!/bin/bash

# Script para ejecutar tests con cobertura y abrir reporte HTML
# Uso: ./scripts/test_coverage.sh [modulo]
# Ejemplo: ./scripts/test_coverage.sh productos

cd "$(dirname "$0")/.."

# Activar entorno virtual si existe
if [ -d "../.venv" ]; then
    source ../.venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Ejecutando Tests con Cobertura ===${NC}\n"

# Si se proporciona módulo, úsalo, sino ejecuta todos los tests
if [ -n "$1" ]; then
    MODULE=$1
    echo -e "${YELLOW}Módulo: $MODULE${NC}\n"
    python manage.py test "$MODULE" -v 2
    python -m coverage run --source="$MODULE" manage.py test "$MODULE"
else
    echo -e "${YELLOW}Ejecutando todos los tests${NC}\n"
    python manage.py test -v 2
    python -m coverage run --source='.' manage.py test
fi

# Verificar si los tests pasaron
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ Tests completados exitosamente${NC}\n"
    
    # Generar reporte en consola
    echo -e "${BLUE}=== Reporte de Cobertura ===${NC}\n"
    python -m coverage report
    
    # Generar reporte HTML
    echo -e "\n${BLUE}Generando reporte HTML...${NC}"
    python -m coverage html
    
    # Abrir reporte en navegador
    if [ -f "htmlcov/index.html" ]; then
        echo -e "${GREEN}✓ Reporte HTML generado en htmlcov/index.html${NC}"
        echo -e "${BLUE}Abriendo reporte en navegador...${NC}\n"
        open htmlcov/index.html
    fi
else
    echo -e "\n${YELLOW}⚠ Los tests fallaron. Revisa los errores arriba.${NC}\n"
    exit 1
fi
