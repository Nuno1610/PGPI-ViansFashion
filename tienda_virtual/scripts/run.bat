@echo off
SETLOCAL

REM --- Configuración de Rutas ---
SET SCRIPT_DIR=%~dp0
REM SRC_DIR apunta a src/
SET SRC_DIR=%SCRIPT_DIR%..
REM ROOT_DIR apunta a la raíz del proyecto
SET ROOT_DIR=%SRC_DIR%\..

REM --- Verificación del Entorno ---
IF NOT EXIST "%ROOT_DIR%\.venv\Scripts\activate.bat" (
    echo [ERROR] No se encontro el entorno virtual en la raiz.
    echo Por favor, ejecuta primero setup.bat
    pause
    exit /b 1
)

echo Activando entorno virtual...
call "%ROOT_DIR%\.venv\Scripts\activate"

echo Iniciando servidor Django...
REM "%*"
python "%SRC_DIR%\manage.py" runserver %*

ENDLOCAL