@echo off
title Agendar Postagens Automaticas no Windows
echo Criando agendamentos diarios no Windows Task Scheduler (08:00, 14:00, 20:00)...
schtasks /create /tn "YouTubeShorts_Manha" /tr "C:\Py\youtube_shorts_automation\executar_postagem_diaria.bat" /sc daily /st 08:00 /f
schtasks /create /tn "YouTubeShorts_Tarde" /tr "C:\Py\youtube_shorts_automation\executar_postagem_diaria.bat" /sc daily /st 14:00 /f
schtasks /create /tn "YouTubeShorts_Noite" /tr "C:\Py\youtube_shorts_automation\executar_postagem_diaria.bat" /sc daily /st 20:00 /f
echo.
echo Sucesso! As 3 tarefas foram agendadas no seu Windows.
echo O seu computador agora postara automaticamente todos os dias as 08:00, 14:00 e 20:00!
pause
