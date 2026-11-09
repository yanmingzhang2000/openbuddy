# FrameMind Start Script
param([string]$Action = "start")

function Show-Help {
    Write-Host "FrameMind Deployment Script"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\start.ps1          Start all services"
    Write-Host "  .\start.ps1 stop     Stop all services"
    Write-Host "  .\start.ps1 restart  Restart all services"
    Write-Host "  .\start.ps1 logs     View logs"
    Write-Host "  .\start.ps1 clean    Clean all data"
    Write-Host ""
    Write-Host "Services:"
    Write-Host "  Web UI:   http://localhost:3000"
    Write-Host "  API Docs: http://localhost:8000/docs"
    Write-Host ""
}

function Test-Docker {
    docker --version 2>$null
    docker compose version 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker not installed. Please install Docker Desktop."
        exit 1
    }
}

function Test-EnvFile {
    if (-not (Test-Path ".env")) {
        Write-Host "Creating .env file..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env" -ForegroundColor Green
    }
}

function Start-Services {
    Write-Host "Starting FrameMind..." -ForegroundColor Cyan
    Test-Docker
    Test-EnvFile
    docker compose up --build -d
    Write-Host ""
    Write-Host "Started!" -ForegroundColor Green
    Write-Host "Web UI: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "API:    http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
}

function Stop-Services {
    Write-Host "Stopping..." -ForegroundColor Cyan
    docker compose down
    Write-Host "Stopped" -ForegroundColor Green
}

function Restart-Services {
    Stop-Services
    Start-Services
}

function Show-Logs {
    docker compose logs -f
}

function Clean-All {
    Write-Host "WARNING: This will delete all data!" -ForegroundColor Red
    $confirm = Read-Host "Type 'yes' to confirm"
    if ($confirm -eq "yes") {
        docker compose down -v
        Write-Host "Cleaned" -ForegroundColor Green
    }
}

switch ($Action.ToLower()) {
    "start"   { Start-Services }
    "stop"    { Stop-Services }
    "restart" { Restart-Services }
    "logs"    { Show-Logs }
    "clean"   { Clean-All }
    "help"    { Show-Help }
    default   { Show-Help; exit 1 }
}
