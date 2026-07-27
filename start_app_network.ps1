param(
    [int]$MPFM_PORT = 8765,
    [string]$MPFM_PUBLIC_HOST = ""
)

Set-Location -Path $PSScriptRoot

$MPFM_BIND_HOST = "0.0.0.0"
$LOCAL_URL = "http://127.0.0.1`:$MPFM_PORT"
$PID_FILE = ".tmp_server_pid.txt"
$LOG_OUT = ".tmp_server_out.log"
$LOG_ERR = ".tmp_server_err.log"

function Get-NetworkIPv4Addresses {
    $configs = Get-NetIPConfiguration -ErrorAction SilentlyContinue |
        Where-Object { $_.IPv4Address -and $_.NetAdapter.Status -eq 'Up' }

    $addresses = @()
    foreach ($config in $configs) {
        foreach ($entry in $config.IPv4Address) {
            $ip = [string]$entry.IPAddress
            if ($ip -and -not $ip.StartsWith('127.') -and -not $ip.StartsWith('169.254.')) {
                $addresses += $ip
            }
        }
    }

    return $addresses | Select-Object -Unique
}

$networkIps = @(Get-NetworkIPv4Addresses)
if (-not $MPFM_PUBLIC_HOST) {
    if ($networkIps.Count -gt 0) {
        $MPFM_PUBLIC_HOST = $networkIps[0]
    }
    else {
        $MPFM_PUBLIC_HOST = $env:COMPUTERNAME
    }
}

$PUBLIC_URL = "http://$MPFM_PUBLIC_HOST`:$MPFM_PORT"

Write-Host ""
Write-Host " ========================================="
Write-Host "   MPFM MANAGER - Modo Rede"
Write-Host " ========================================="
Write-Host ""

$pythonCheck = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host " [ERRO] Python nao encontrado."
    Write-Host " Instale em: https://www.python.org/downloads/"
    Read-Host "Pressione Enter para sair"
    exit 1
}

Write-Host " Verificando dependencias..."
python -m pip install fastapi uvicorn python-multipart PyPDF2 pandas openpyxl numpy --quiet

Write-Host " Verificando porta $MPFM_PORT..."
$portCheck = Get-NetTCPConnection -LocalPort $MPFM_PORT -State Listen -ErrorAction SilentlyContinue
if ($portCheck) {
    Write-Host ""
    Write-Host " [ERRO] A porta $MPFM_PORT ja esta em uso."
    Write-Host " Feche o processo atual antes de iniciar o modo rede."
    Write-Host ""
    Read-Host "Pressione Enter para sair"
    exit 1
}

if (Test-Path $PID_FILE) { Remove-Item $PID_FILE -Force }
if (Test-Path $LOG_OUT) { Remove-Item $LOG_OUT -Force }
if (Test-Path $LOG_ERR) { Remove-Item $LOG_ERR -Force }

Write-Host ""
Write-Host " Iniciando servidor em segundo plano..."
Write-Host " Bind host:   $MPFM_BIND_HOST"
Write-Host " URL local:   $LOCAL_URL"
Write-Host " URL publica: $PUBLIC_URL"
Write-Host " Logs:        $LOG_OUT"
Write-Host " PID:         $PID_FILE"
Write-Host ""

$env:MPFM_PORT = [string]$MPFM_PORT
$env:MPFM_HOST = $MPFM_BIND_HOST
$env:MPFM_PUBLIC_BASE_URL = $PUBLIC_URL

$proc = Start-Process python -ArgumentList "server.py" -PassThru -WindowStyle Hidden -RedirectStandardOutput $LOG_OUT -RedirectStandardError $LOG_ERR
$proc.Id | Out-File -FilePath $PID_FILE

Write-Host " Aguardando servidor inicializar..."

$ready = $false
for ($i = 0; $i -lt 25; $i++) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "$LOCAL_URL/api/health" -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    }
    catch {
    }
    Start-Sleep -Seconds 1
}

if (-not $ready) {
    Write-Host " [ERRO] O servidor nao respondeu ao health check."
    if (Test-Path $LOG_ERR) {
        Write-Host ""
        Write-Host " Ultimas linhas do erro:"
        Get-Content $LOG_ERR -Tail 20
    }
    Read-Host "Pressione Enter para sair"
    exit 1
}

Write-Host ""
Write-Host " Servidor pronto."
Write-Host " Acesso nesta maquina:"
Write-Host "   $LOCAL_URL"
Write-Host ""
Write-Host " Acesso pelas outras maquinas:"
if ($networkIps.Count -gt 0) {
    foreach ($ip in $networkIps) {
        Write-Host "   http://$ip`:$MPFM_PORT"
    }
}
else {
    Write-Host "   http://$MPFM_PUBLIC_HOST`:$MPFM_PORT"
}
Write-Host ""
Write-Host " Se outro computador nao abrir, liberar a porta $MPFM_PORT/TCP no Firewall do Windows da maquina host."
Write-Host ""

Start-Process $LOCAL_URL

Write-Host " Para parar depois:"
Write-Host "   Stop-Process -Id (Get-Content $PID_FILE)"
Write-Host ""