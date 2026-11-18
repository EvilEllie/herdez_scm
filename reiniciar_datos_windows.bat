@echo off
chcp 65001 > nul
cd /d "%~dp0"
set PY=python
where python > nul 2> nul || set PY=py
echo Esto borra los datos y deja la base como al inicio de la demo.
pause
%PY% crear_bd.py
pause
