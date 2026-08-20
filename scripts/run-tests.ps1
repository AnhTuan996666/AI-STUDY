# Chạy toàn bộ test tự động của 3 layer.
# Không cần Ollama — mọi test đều dùng mock / MockTransport.
#
# Chạy:  .\scripts\run-tests.ps1

$root = Split-Path -Parent $PSScriptRoot
$failed = @()

function Invoke-Suite($name, $path, $command) {
    Write-Host ""
    Write-Host "=== $name ===" -ForegroundColor Cyan
    Set-Location $path
    & $command
    if ($LASTEXITCODE -ne 0) {
        $script:failed += $name
        Write-Host "$name : FAIL" -ForegroundColor Red
    } else {
        Write-Host "$name : PASS" -ForegroundColor Green
    }
}

Invoke-Suite "Model layer (pytest)" "$root\model" {
    & .\.venv\Scripts\python.exe -m pytest -q
}

Invoke-Suite "Backend (pytest)" "$root\backend" {
    & .\.venv\Scripts\python.exe -m pytest -q
}

Invoke-Suite "Frontend (typecheck)" "$root\frontend" { npm run typecheck }
Invoke-Suite "Frontend (lint)"      "$root\frontend" { npm run lint }
Invoke-Suite "Frontend (build)"     "$root\frontend" { npm run build }

Set-Location $root

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
if ($failed.Count -eq 0) {
    Write-Host "TAT CA TEST DEU PASS" -ForegroundColor Green
    exit 0
}

Write-Host "CO $($failed.Count) NHOM TEST THAT BAI:" -ForegroundColor Red
$failed | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
exit 1
