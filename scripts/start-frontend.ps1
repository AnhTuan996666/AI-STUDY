# Chạy frontend Next.js ở chế độ dev.
#
# Chạy:  .\scripts\start-frontend.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\frontend"

if (-not (Test-Path node_modules)) {
    Write-Host "Chua cai node_modules. Chay .\scripts\setup.ps1 truoc." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path .env.local)) { Copy-Item .env.local.example .env.local }

Write-Host "Frontend : http://localhost:3000" -ForegroundColor Cyan
Write-Host "Backend  : $((Get-Content .env.local | Select-String 'NEXT_PUBLIC_API_BASE_URL').Line)" -ForegroundColor DarkGray
Write-Host ""

npm run dev
