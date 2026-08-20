# Chạy backend FastAPI ở chế độ dev (tự reload khi sửa code).
#
# Chạy:
#   .\scripts\start-backend.ps1              # dùng cấu hình trong backend\.env
#   .\scripts\start-backend.ps1 -Mock        # ép dùng provider mock (không cần Ollama)
#   .\scripts\start-backend.ps1 -Port 8080

param(
    [switch]$Mock,
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\backend"

if (-not (Test-Path .venv)) {
    Write-Host "Chua co venv. Chay .\scripts\setup.ps1 truoc." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path .env)) { Copy-Item .env.example .env }

if ($Mock) {
    $env:LLM_PROVIDER = 'mock'
    Write-Host "Che do MOCK: khong goi model that." -ForegroundColor Yellow
}

Write-Host "Backend  : http://localhost:$Port" -ForegroundColor Cyan
Write-Host "Swagger  : http://localhost:$Port/docs" -ForegroundColor Cyan
Write-Host "Health   : http://localhost:$Port/api/v1/health" -ForegroundColor Cyan
Write-Host ""

& .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port $Port
