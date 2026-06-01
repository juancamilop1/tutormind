@echo off
cd /d "%~dp0backend"
echo Instalando dependencias si hace falta...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo ERROR: no se pudieron instalar las dependencias de Python.
  pause
  exit /b 1
)
echo.
echo Iniciando TutorMind API en http://127.0.0.1:8000
echo (deja esta ventana abierta mientras usas el chat)
echo Prueba en el navegador: http://127.0.0.1:8000/api/health
echo.
python -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
