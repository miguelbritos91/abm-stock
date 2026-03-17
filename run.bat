@echo off
echo Instalando dependencias...
pip install -r requirements.txt
echo.
echo Iniciando ABM Stock...
python main.py
pause
