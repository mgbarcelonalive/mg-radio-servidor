@echo off
title MG BARCELONA LIVE - SERVIDOR NUBE (PRUEBA LOCAL)
cd /d "%~dp0"
start "" "http://localhost:8080/panel"
py -3.14 servidor_nube.py
pause
