# Script para iniciar a aplicação MPFM
Set-Location -Path $PSScriptRoot

# Variáveis de configuração
$MPFM_PORT = "8765"
$MPFM_HOST = "127.0.0.1"
$MPFM_URL = "http://$MPFM_HOST`:$MPFM_PORT"
$PID_FILE = ".tmp_server_pid.txt"
$LOG_OUT = ".tmp_server_out.log"
$LOG_ERR = ".tmp_server_err.log"

Write-Host ""
Write-Host " ========================================="
Write-Host "   MPFM MANAGER - Bacalhau FPSO"
Write-Host " ========================================="
Write-Host ""

# Verificar Python
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
$portCheck = netstat -ano | Select-String ":$MPFM_PORT " | Select-String "LISTENING"
if ($portCheck) {
    Write-Host ""
    Write-Host " [ERRO] A porta $MPFM_PORT ja esta em uso."
    Write-Host " Feche o processo que esta usando a porta ou libere a $MPFM_PORT antes de iniciar."
    Write-Host ""
    Read-Host "Pressione Enter para sair"
    exit 1
}

# Limpar arquivos antigos
if (Test-Path $PID_FILE) { Remove-Item $PID_FILE -Force }
if (Test-Path $LOG_OUT) { Remove-Item $LOG_OUT -Force }
if (Test-Path $LOG_ERR) { Remove-Item $LOG_ERR -Force }

Write-Host ""
Write-Host " Iniciando servidor em segundo plano..."
Write-Host " URL:   $MPFM_URL"
Write-Host " Logs:  $LOG_OUT"
Write-Host " PID:   $PID_FILE"
Write-Host ""

# Iniciar servidor
$env:MPFM_PORT = $MPFM_PORT
$env:MPFM_HOST = $MPFM_HOST
$env:MPFM_PUBLIC_BASE_URL = $MPFM_URL

$proc = Start-Process python -ArgumentList "server.py" -PassThru -WindowStyle Hidden -RedirectStandardOutput $LOG_OUT -RedirectStandardError $LOG_ERR
$proc.Id | Out-File -FilePath $PID_FILE

Write-Host " Aguardando servidor initializar..."

# Aguardar servidor estar pronto
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "$MPFM_URL/api/health" -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        # Servidor ainda não está pronto
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

Write-Host " Servidor pronto em $MPFM_URL"
Write-Host ""

# Abrir navegador
Start-Process $MPFM_URL

Write-Host " Para parar depois:"
Write-Host "   Stop-Process -Id (Get-Content $PID_FILE)"
Write-Host ""
