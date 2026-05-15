# JARVIS — Lanceur PowerShell
# Usage : .\desktop\launch.ps1

$Root = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "  ===================================" -ForegroundColor Cyan
Write-Host "   J.A.R.V.I.S  —  Initialisation  " -ForegroundColor Cyan
Write-Host "  ===================================" -ForegroundColor Cyan
Write-Host ""

# 1. Docker
Write-Host "[1/3] Démarrage des services Docker..." -ForegroundColor DarkCyan
try {
    & docker compose -f "$Root\docker-compose.yml" up -d 2>&1 | Out-Null
    Write-Host "      Services Docker démarrés." -ForegroundColor Green
} catch {
    Write-Host "      Docker non disponible — mode standalone." -ForegroundColor Yellow
}

# 2. Attente
Write-Host "[2/3] Attente des services (6 secondes)..." -ForegroundColor DarkCyan
Start-Sleep -Seconds 6

# 3. App
Write-Host "[3/3] Lancement de l'interface JARVIS..." -ForegroundColor DarkCyan
Write-Host ""
& python "$PSScriptRoot\app.py"
