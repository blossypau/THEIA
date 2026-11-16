@echo off
setlocal
cd /d "%~dp0"
echo THEIA - Inicio local para Windows
echo.
if exist ".venv\Scripts\python.exe" goto check_runtime
goto install_runtime

:check_runtime
".venv\Scripts\python.exe" -c "import sys, streamlit, sqlalchemy, pandas, scipy, sklearn, requests, pydantic, reportlab; assert sys.version_info[:2] == (3, 14); assert streamlit.__version__ == '1.67.0'; assert sqlalchemy.__version__ == '2.1.8'"
if not errorlevel 1 goto start_services

:install_runtime
py -3.14 -c "import sys"
if errorlevel 1 goto missing_python
echo Instalando dependencias. La primera vez requiere Internet y puede tardar varios minutos.
py -3.14 scripts\install_windows.py --pure-python-sqlalchemy
if errorlevel 1 goto failed

:start_services
echo.
echo Abre http://localhost:8507 cuando aparezca HTTP ready: THEIA.
echo Conserva esta ventana abierta. Ctrl+C detiene solo los servicios iniciados aqui.
echo OHIF es opcional y requiere su instalacion externa; consulta docs\INICIO_RAPIDO.md.
".venv\Scripts\python.exe" scripts\start_theia_services.py
if errorlevel 1 goto failed
exit /b 0

:missing_python
echo.
echo Falta Python 3.14 con el lanzador de Windows.
echo Instalalo desde https://www.python.org/downloads/windows/ y vuelve a abrir este archivo.
echo No se ha modificado la configuracion de seguridad de Windows.
pause
exit /b 1

:failed
echo.
echo THEIA no pudo iniciar. Conserva el error que aparece arriba para revisarlo.
pause
exit /b 1
