@echo off
cd /d "C:\Py\youtube_shorts_automation"
echo [%date% %time%] Iniciando geracao e postagem automatica do Short... >> log_postagens.txt
call .venv\Scripts\activate.bat
python main.py --niche facts --upload >> log_postagens.txt 2>&1
echo [%date% %time%] Finalizado! >> log_postagens.txt
