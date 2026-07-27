@echo off
setlocal
title MPFM Manager - Modo Rede
color 0A
cd /d "%~dp0"

set "MPFM_PORT=8765"
set "MPFM_HOST=0.0.0.0"
set "MPFM_LOCAL_URL=http://127.0.0.1:%MPFM_PORT%"
set "MPFM_PUBLIC_HOST="
set "MPFM_PUBLIC_BASE_URL="
set "PORT_PID="
set "PID_FILE=%CD%\.tmp_server_pid.txt"
set "LOG_OUT=%CD%\.tmp_server_out.log"
set "LOG_ERR=%CD%\.tmp_server_err.log"

echo.
echo  =========================================
echo    MPFM MANAGER - Modo Rede
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

echo  Descobrindo IP da maquina host...
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$configs = Get-NetIPConfiguration -ErrorAction SilentlyContinue ^| Where-Object { $_.IPv4Address -and $_.NetAdapter.Status -eq 'Up' }; $ips = @(); foreach ($cfg in $configs) { foreach ($entry in $cfg.IPv4Address) { $ip = [string]$entry.IPAddress; if ($ip -and -not $ip.StartsWith('127.') -and -not $ip.StartsWith('169.254.')) { $ips += $ip } } }; $ips = $ips ^| Select-Object -Unique; if ($ips.Count -gt 0) { $ips[0] } else { $env:COMPUTERNAME }"`) do set "MPFM_PUBLIC_HOST=%%I"

if not defined MPFM_PUBLIC_HOST set "MPFM_PUBLIC_HOST=%COMPUTERNAME%"
set "MPFM_PUBLIC_BASE_URL=http://%MPFM_PUBLIC_HOST%:%MPFM_PORT%"

echo  Verificando porta %MPFM_PORT%...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%MPFM_PORT% " ^| findstr "LISTENING"') do set "PORT_PID=%%P"
if defined PORT_PID (
	echo.
	echo  [ERRO] A porta %MPFM_PORT% ja esta em uso.
	echo  Feche o processo atual antes de iniciar o modo rede.
	echo.
	pause
	exit /b 1
)

if exist "%PID_FILE%" del /f /q "%PID_FILE%" >nul 2>&1
if exist "%LOG_OUT%" del /f /q "%LOG_OUT%" >nul 2>&1
if exist "%LOG_ERR%" del /f /q "%LOG_ERR%" >nul 2>&1

echo.
echo  Iniciando servidor em segundo plano...
echo  Bind host:   %MPFM_HOST%
echo  URL local:   %MPFM_LOCAL_URL%
echo  URL publica: %MPFM_PUBLIC_BASE_URL%
echo  Logs:        %LOG_OUT%
echo  PID:         %PID_FILE%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$env:MPFM_PORT='%MPFM_PORT%';" ^
  "$env:MPFM_HOST='%MPFM_HOST%';" ^
  "$env:MPFM_PUBLIC_BASE_URL='%MPFM_PUBLIC_BASE_URL%';" ^
  "$p = Start-Process python -ArgumentList 'server.py' -WorkingDirectory '%CD%' -PassThru -WindowStyle Hidden -RedirectStandardOutput '%LOG_OUT%' -RedirectStandardError '%LOG_ERR%';" ^
  "Set-Content -Path '%PID_FILE%' -Value $p.Id"

if errorlevel 1 (
	echo  [ERRO] Falha ao iniciar o servidor em segundo plano.
	pause
	exit /b 1
)

set "SERVER_READY="
for /L %%I in (1,1,25) do (
	powershell -NoProfile -ExecutionPolicy Bypass -Command ^
	  "try { $r = Invoke-WebRequest -UseBasicParsing '%MPFM_LOCAL_URL%/api/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
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

echo  Servidor pronto.
echo.
echo  Acesso nesta maquina:
echo    %MPFM_LOCAL_URL%
echo.
echo  Acesso pelas outras maquinas:
powershell -NoProfile -ExecutionPolicy Bypass -Command "$configs = Get-NetIPConfiguration -ErrorAction SilentlyContinue ^| Where-Object { $_.IPv4Address -and $_.NetAdapter.Status -eq 'Up' }; $ips = @(); foreach ($cfg in $configs) { foreach ($entry in $cfg.IPv4Address) { $ip = [string]$entry.IPAddress; if ($ip -and -not $ip.StartsWith('127.') -and -not $ip.StartsWith('169.254.')) { $ips += $ip } } }; $ips = $ips ^| Select-Object -Unique; if ($ips.Count -eq 0) { Write-Host '   http://%MPFM_PUBLIC_HOST%:%MPFM_PORT%' } else { foreach ($ip in $ips) { Write-Host ('   http://{0}:%MPFM_PORT%' -f $ip) } }"
echo.
echo  Se outro computador nao abrir, liberar a porta %MPFM_PORT%/TCP no Firewall do Windows da maquina host.
echo.

start "" "%MPFM_LOCAL_URL%"

echo  Para parar depois:
echo    taskkill /PID ^<PID do arquivo .tmp_server_pid.txt^> /F
echo.
endlocal
exit /b 0