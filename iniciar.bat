@echo off
setlocal
title MPFM Manager
color 0B
cd /d "%~dp0"

set "MPFM_PORT=8765"
set "MPFM_HOST=127.0.0.1"
set "MPFM_URL=http://%MPFM_HOST%:%MPFM_PORT%"
set "PORT_PID="
set "PID_FILE=%CD%\.tmp_server_pid.txt"
set "LOG_OUT=%CD%\.tmp_server_out.log"
set "LOG_ERR=%CD%\.tmp_server_err.log"

echo.
echo  =========================================
echo    MPFM MANAGER - Bacalhau FPSO
echo  =========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] Python nao encontrado.
    echo  Instale em: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo  Verificando dependencias...
python -m pip install fastapi uvicorn python-multipart PyPDF2 pandas openpyxl numpy --quiet

echo  Verificando porta %MPFM_PORT%...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%MPFM_PORT% " ^| findstr "LISTENING"') do set "PORT_PID=%%P"
if defined PORT_PID (
    echo.
    echo  [ERRO] A porta %MPFM_PORT% ja esta em uso.
    echo  Feche o processo que esta usando a porta ou libere a %MPFM_PORT% antes de iniciar.
    echo  Dica:
    echo    netstat -ano ^| findstr :%MPFM_PORT%
    echo    tasklist /FI "PID eq %PORT_PID%"
    echo    Stop-Process -Id %PORT_PID% -Force
    echo.
    pause
    exit /b 1
)

if exist "%PID_FILE%" del /f /q "%PID_FILE%" >nul 2>&1
if exist "%LOG_OUT%" del /f /q "%LOG_OUT%" >nul 2>&1
if exist "%LOG_ERR%" del /f /q "%LOG_ERR%" >nul 2>&1

echo.
echo  Iniciando servidor em segundo plano...
echo  URL:   %MPFM_URL%
echo  Logs:  %LOG_OUT%
echo  PID:   %PID_FILE%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$env:MPFM_PORT='%MPFM_PORT%';" ^
  "$env:MPFM_HOST='%MPFM_HOST%';" ^
  "$env:MPFM_PUBLIC_BASE_URL='%MPFM_URL%';" ^
  "$p = Start-Process python -ArgumentList 'server.py' -WorkingDirectory '%CD%' -PassThru -WindowStyle Hidden -RedirectStandardOutput '%LOG_OUT%' -RedirectStandardError '%LOG_ERR%';" ^
  "Set-Content -Path '%PID_FILE%' -Value $p.Id"

if errorlevel 1 (
    echo  [ERRO] Falha ao iniciar o servidor em segundo plano.
    pause
    exit /b 1
)

set "SERVER_READY="
for /L %%I in (1,1,20) do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "try { $r = Invoke-WebRequest -UseBasicParsing '%MPFM_URL%/api/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
    if not errorlevel 1 (
        set "SERVER_READY=1"
        goto :server_ready
    )
    timeout /t 1 >nul
)

:server_ready
if not defined SERVER_READY (
    echo  [ERRO] O servidor nao respondeu ao health check.
    if exist "%LOG_ERR%" (
        echo.
        echo  Ultimas linhas do erro:
        powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Content '%LOG_ERR%' -Tail 20"
    )
    pause
    exit /b 1
)

start "" "%MPFM_URL%"

echo  Servidor pronto.
echo  Para parar depois:
echo    taskkill /PID ^<PID do arquivo .tmp_server_pid.txt^> /F
echo.
endlocal
exit /b 0
