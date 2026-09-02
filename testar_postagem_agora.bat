@echo off
title Testar Geracao e Postagem no YouTube
cd /d "C:\Py\youtube_shorts_automation"
call .venv\Scripts\activate.bat
python main.py --niche facts --upload
pause
