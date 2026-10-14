@echo off
REM Script para ejecutar tests con cobertura y abrir reporte HTML en Windows
REM Uso: scripts\test_coverage.bat [modulo]
REM Ejemplo: scripts\test_coverage.bat productos

cd /d "%~dp0\.."

REM Activar entorno virtual si existe
if exist "..\\.venv\\Scripts\\activate.bat" (
    call ..\\.venv\\Scripts\\activate.bat
) else if exist ".venv\\Scripts\\activate.bat" (
    call .venv\\Scripts\\activate.bat
)

echo === Ejecutando Tests con Cobertura ===
echo.

if "%1"=="" (
    echo Ejecutando todos los tests
    echo.
    python manage.py test -v 2
    python -m coverage run --source="." manage.py test
) else (
    echo Modulo: %1
    echo.
    python manage.py test %1 -v 2
    python -m coverage run --source="%1" manage.py test %1
)

if %errorlevel% equ 0 (
    echo.
    echo [OK] Tests completados exitosamente
    echo.
    
    echo === Reporte de Cobertura ===
    echo.
    python -m coverage report
    
    echo.
    echo Generando reporte HTML...
    python -m coverage html
    
    if exist htmlcov\index.html (
        echo [OK] Reporte HTML generado en htmlcov\index.html
        echo Abriendo reporte en navegador...
        echo.
        start htmlcov\index.html
    )
) else (
    echo.
    echo [ERROR] Los tests fallaron. Revisa los errores arriba.
    echo.
    exit /b 1
)
