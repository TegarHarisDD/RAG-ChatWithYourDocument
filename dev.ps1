# Starts the whole stack locally with one command.
#
#   .\dev.ps1
#
# First run creates the Python virtualenv, installs backend and frontend
# dependencies, and (if missing) copies .env.example to .env. The database is
# MongoDB Atlas, configured via MONGODB_URI in .env — no local database
# process is required.

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path "backend\.venv")) {
    Write-Host "Creating Python virtualenv..." -ForegroundColor Cyan
    python -m venv backend\.venv
    & "backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
    & "backend\.venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Warning "Created .env from .env.example. Fill in MONGODB_URI (and OPENROUTER_API_KEY), then re-run .\dev.ps1."
    exit 1
}

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing root tooling..." -ForegroundColor Cyan
    npm.cmd install
}

if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    npm.cmd --prefix frontend install
}

Write-Host "Starting backend (http://localhost:8000) and frontend (http://localhost:5173)..." -ForegroundColor Green
npm.cmd run dev
