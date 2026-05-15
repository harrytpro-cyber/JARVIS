@echo off
title JARVIS — Démarrage
color 0B
echo.
echo  ===================================
echo   J.A.R.V.I.S  —  Initialisation
echo  ===================================
echo.

echo [1/3] Démarrage des services Docker...
docker compose -f "%~dp0..\docker-compose.yml" up -d
if errorlevel 1 (
    echo [!] Docker non disponible — mode standalone activé
)

echo [2/3] Attente des services (5 secondes)...
timeout /t 5 /nobreak >nul

echo [3/3] Lancement de l'interface JARVIS...
python "%~dp0app.py"

pause
