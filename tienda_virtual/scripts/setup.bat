@echo off
SETLOCAL

REM Obtener la ruta del script
SET SCRIPT_DIR=%~dp0
REM SRC_DIR apunta a src/
SET SRC_DIR=%SCRIPT_DIR%..
REM ROOT_DIR apunta a la raíz del proyecto
SET ROOT_DIR=%SRC_DIR%\..

echo Creando entorno virtual en la raíz
py -3.12 -m venv "%ROOT_DIR%\.venv"

echo Activando entorno virtual
call "%ROOT_DIR%\.venv\Scripts\activate"

echo Instalando dependencias desde src/requirements.txt
python -m pip install --upgrade pip
python -m pip install -r "%SRC_DIR%\requirements.txt"

echo Ejecutando migraciones
python "%SRC_DIR%\manage.py" migrate || goto :error

echo Generando datos de prueba
python "%SRC_DIR%\manage.py" runscript crear_datos_prueba || goto :error

echo PROCESO COMPLETADO CORRECTAMENTE
goto :end

:error
echo ERROR DURANTE EL SETUP
exit /b 1

:end
ENDLOCAL
