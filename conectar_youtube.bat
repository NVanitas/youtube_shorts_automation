@echo off
title Autorizar YouTube - Nicosaurus
cd /d "%~dp0"
echo Iniciando o autorizador do YouTube...
call .venv\Scripts\activate.bat
python auth_helper.py
pause
