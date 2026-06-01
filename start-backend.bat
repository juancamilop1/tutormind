@echo off
cd /d "%~dp0backend"
echo Instalando dependencias si hace falta...
pip install -r requirements.txt -q
echo.
echo Iniciando TutorMind API en http://127.0.0.1:8000
echo (deja esta ventana abierta mientras usas el chat)
echo.
uvicorn main:app --reload --host 127.0.0.1 --port 8000
pause
