# PayCrew ngrok stress test — run while backend + ngrok are up.
# Usage: .\scripts\stress_test_ngrok.ps1 [-PublicUrl "https://xxx.ngrok-free.dev"]

param(
    [string]$PublicUrl = "",
    [int]$Requests = 20
)

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot\..

function Get-NgrokUrl {
    try {
        $tunnels = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 5
        return ($tunnels.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1).public_url
    } catch {
        return $null
    }
}

Write-Host "=== PayCrew ngrok stress test ===" -ForegroundColor Cyan

# 1. Local backend
Write-Host "`n[1] Local backend (127.0.0.1:8000)..."
try {
    $local = Invoke-WebRequest -Uri "http://127.0.0.1:8000/docs" -UseBasicParsing -TimeoutSec 5
    Write-Host "    OK  /docs -> $($local.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "    FAIL backend not reachable: $_" -ForegroundColor Red
    exit 1
}

# 2. ngrok agent
Write-Host "`n[2] ngrok agent (127.0.0.1:4040)..."
$url = if ($PublicUrl) { $PublicUrl.TrimEnd("/") } else { Get-NgrokUrl }
if (-not $url) {
    Write-Host "    FAIL ngrok not running. Start: ngrok http 8000" -ForegroundColor Red
    exit 1
}
Write-Host "    OK  tunnel -> $url" -ForegroundColor Green

$headers = @{ "ngrok-skip-browser-warning" = "true" }

# 3. Public /docs
Write-Host "`n[3] Public /docs..."
try {
    $docs = Invoke-WebRequest -Uri "$url/docs" -Headers $headers -UseBasicParsing -TimeoutSec 15
    Write-Host "    OK  /docs -> $($docs.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "    FAIL $url/docs : $_" -ForegroundColor Red
    Write-Host "    Try: ngrok diagnose | restart ngrok" -ForegroundColor Yellow
}

# 4. Public login
Write-Host "`n[4] Public POST /v1/auth/login..."
try {
    $login = Invoke-RestMethod -Uri "$url/v1/auth/login" -Method POST `
        -ContentType "application/json" -Headers $headers `
        -Body '{"code":"AP2024"}' -TimeoutSec 15
    Write-Host "    OK  token received, role=$($login.role)" -ForegroundColor Green
    $token = $login.token
} catch {
    Write-Host "    FAIL login: $_" -ForegroundColor Red
    $token = $null
}

# 5. Authenticated stats
if ($token) {
    Write-Host "`n[5] Public GET /v1/ap/stats..."
    try {
        $stats = Invoke-RestMethod -Uri "$url/v1/ap/stats" -Headers @{
            "Authorization" = "Bearer $token"
            "ngrok-skip-browser-warning" = "true"
        } -TimeoutSec 15
        Write-Host "    OK  total=$($stats.total)" -ForegroundColor Green
    } catch {
        Write-Host "    FAIL stats: $_" -ForegroundColor Red
    }
}

# 6. Burst requests
Write-Host "`n[6] Burst $Requests requests to /docs..."
$ok = 0; $fail = 0
1..$Requests | ForEach-Object {
    try {
        $r = Invoke-WebRequest -Uri "$url/docs" -Headers $headers -UseBasicParsing -TimeoutSec 15
        if ($r.StatusCode -eq 200) { $ok++ } else { $fail++ }
    } catch { $fail++ }
}
Write-Host "    $ok OK / $fail FAIL" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Yellow" })

Write-Host "`n=== Share with Shresth ===" -ForegroundColor Cyan
Write-Host "  Base:     $url/v1"
Write-Host "  Swagger:  $url/docs"
Write-Host "  WS:       wss://$($url -replace '^https://','')/v1/ws?token=TOKEN"
Write-Host "  Header:   ngrok-skip-browser-warning: true"
