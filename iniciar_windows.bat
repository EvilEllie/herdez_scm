@echo off
chcp 65001 > nul
cd /d "%~dp0"
set PY=python
where python > nul 2> nul || set PY=py
echo Instalando lo necesario (solo tarda la primera vez)...
%PY% -m pip install -r requirements.txt --quiet
echo.
start "" cmd /c "timeout /t 5 > nul & start http://localhost:5000"
%PY% app.py
pause
