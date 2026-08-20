# Setup toàn bộ project: venv + pip + npm + file .env
# Chạy:  .\scripts\setup.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

function Write-Step($text) {
    Write-Host ""
    Write-Host "=== $text ===" -ForegroundColor Cyan
}

function Copy-EnvFile($source, $target) {
    if (Test-Path $target) {
        Write-Host "  giữ nguyên $(Split-Path $target -Leaf) (đã có)" -ForegroundColor DarkGray
    } else {
        Copy-Item $source $target
        Write-Host "  đã tạo $(Split-Path $target -Leaf)" -ForegroundColor Green
    }
}

# --- model layer ---------------------------------------------------------
Write-Step "1/3  Model layer (Python + Ollama)"
Set-Location "$root\model"
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip -q
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt -q
Copy-EnvFile ".env.example" ".env"
Write-Host "  OK" -ForegroundColor Green

# --- backend -------------------------------------------------------------
Write-Step "2/3  Backend (FastAPI)"
Set-Location "$root\backend"
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip -q
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt -q
Copy-EnvFile ".env.example" ".env"
Write-Host "  OK" -ForegroundColor Green

# --- frontend ------------------------------------------------------------
Write-Step "3/3  Frontend (Next.js)"
Set-Location "$root\frontend"
npm install --no-fund --no-audit
Copy-EnvFile ".env.local.example" ".env.local"
Write-Host "  OK" -ForegroundColor Green

Set-Location $root

Write-Host ""
Write-Host "=== HOÀN TẤT ===" -ForegroundColor Green
Write-Host ""
Write-Host "Bước tiếp theo:"
Write-Host "  1. Cài Ollama + pull model  ->  xem REMIND.md muc 0"
Write-Host "  2. Chay backend             ->  .\scripts\start-backend.ps1"
Write-Host "  3. Chay frontend            ->  .\scripts\start-frontend.ps1"
Write-Host "  4. Chay toan bo test        ->  .\scripts\run-tests.ps1"
Write-Host ""
Write-Host "Chua co Ollama? Dat LLM_PROVIDER=mock trong backend\.env de van chay duoc." -ForegroundColor Yellow
