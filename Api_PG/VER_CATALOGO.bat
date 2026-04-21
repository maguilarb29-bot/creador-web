@echo off
cd /d "%~dp0"
echo Iniciando servidor...
start /b python -m http.server 8888
timeout /t 2 /nobreak > /dev/null
start "" "http://localhost:8888/solaris_catalogo.html"
echo Servidor activo en http://localhost:8888
echo Cierra esta ventana para detener el servidor.
python -m http.server 8889 > /dev/null 2>&1
