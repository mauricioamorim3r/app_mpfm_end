@echo off
setlocal EnableDelayedExpansion
title MPFM Manager
color 0B
cd /d "%~dp0"

set "MPFM_PORT=8765"
set "SETUP_FLAG=%CD%\.mpfm_setup_done"
set "LOGFILE=%CD%\mpfm_inicio.log"

:: Limpa log anterior e registra inicio
echo [%DATE% %TIME%] MPFM.bat iniciado > "%LOGFILE%"
echo  Pasta: %CD% >> "%LOGFILE%"

echo.
echo  =====================================================
echo    MPFM MANAGER - Bacalhau FPSO
echo  =====================================================
echo.
echo  Log: mpfm_inicio.log
echo.

:: ── Verifica Python ──────────────────────────────────────────────────────────
echo [%DATE% %TIME%] Verificando Python... >> "%LOGFILE%"
python --version >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    :: Tenta com 'py' launcher (Windows Launcher)
    py --version >> "%LOGFILE%" 2>&1
    if errorlevel 1 (
        echo  [ERRO] Python nao encontrado no sistema.
        echo  [ERRO] Solicite ao TI a instalacao do Python 3.10+
        echo.
        echo  [ERRO] Python nao encontrado >> "%LOGFILE%"
        echo.
        echo  Pressione qualquer tecla para fechar...
        pause >nul
        exit /b 1
    )
    set "PYTHON_CMD=py"
) else (
    set "PYTHON_CMD=python"
)
echo [%DATE% %TIME%] Python OK: %PYTHON_CMD% >> "%LOGFILE%"
echo  Python OK: %PYTHON_CMD%

:: ── Primeira execucao: instala pacotes para o usuario (sem admin) ────────────
if not exist "%SETUP_FLAG%" (
    echo.
    echo  -------------------------------------------------------
    echo  PRIMEIRA EXECUCAO: instalando pacotes necessarios...
    echo  ^(Pode demorar 2-5 minutos. Nao feche esta janela.^)
    echo  -------------------------------------------------------
    echo.
    echo [%DATE% %TIME%] Iniciando pip install --user >> "%LOGFILE%"

    %PYTHON_CMD% -m pip install --user -r "%CD%\requirements.txt" >> "%LOGFILE%" 2>&1
    if errorlevel 1 (
        echo.
        echo  [ERRO] Falha ao instalar pacotes.
        echo  Verifique o arquivo mpfm_inicio.log para detalhes.
        echo  [ERRO] pip install falhou (errorlevel=%ERRORLEVEL%) >> "%LOGFILE%"
        echo.
        echo  Pressione qualquer tecla para fechar...
        pause >nul
        exit /b 1
    )

    echo. > "%SETUP_FLAG%"
    echo [%DATE% %TIME%] Pacotes instalados com sucesso >> "%LOGFILE%"
    echo  Pacotes instalados com sucesso!
    echo.
) else (
    echo  Pacotes ja instalados. Iniciando servidor...
    echo [%DATE% %TIME%] Setup flag encontrado, pulando instalacao >> "%LOGFILE%"
)

:: ── Verifica se a porta ja esta em uso ───────────────────────────────────────
set "PORT_PID="
for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":%MPFM_PORT% " ^| findstr "LISTENING"') do set "PORT_PID=%%P"
if defined PORT_PID (
    echo  [AVISO] Servidor ja esta rodando na porta %MPFM_PORT%. Abrindo navegador...
    echo [%DATE% %TIME%] Porta ja em uso (PID=%PORT_PID%), abrindo navegador >> "%LOGFILE%"
    timeout /t 2 >nul
    powershell -NoProfile -Command "Start-Process 'http://127.0.0.1:%MPFM_PORT%'"
    echo.
    echo  Pressione qualquer tecla para fechar esta janela...
    pause >nul
    exit /b 0
)

:: ── Descobre IP local ─────────────────────────────────────────────────────────
set "LOCAL_IP=127.0.0.1"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$s=New-Object Net.Sockets.UdpClient; try{$s.Connect('10.255.255.255',1);([Net.IPEndPoint]$s.Client.LocalEndPoint).Address.ToString()}catch{'127.0.0.1'}finally{$s.Dispose()}"`) do set "LOCAL_IP=%%I"

set "PUBLIC_URL=http://%LOCAL_IP%:%MPFM_PORT%"
set "LOCAL_URL=http://127.0.0.1:%MPFM_PORT%"

echo.
echo  Esta maquina:        %LOCAL_URL%
echo  Outros computadores: %PUBLIC_URL%
echo.
echo  Mantenha esta janela aberta. Ctrl+C para encerrar.
echo  =====================================================
echo.
echo [%DATE% %TIME%] Iniciando servidor em %PUBLIC_URL% >> "%LOGFILE%"

:: ── Inicia servidor ──────────────────────────────────────────────────────────
set "MPFM_HOST=0.0.0.0"
set "MPFM_PORT=%MPFM_PORT%"
set "MPFM_PUBLIC_BASE_URL=%PUBLIC_URL%"

%PYTHON_CMD% iniciar_standalone.py >> "%LOGFILE%" 2>&1

echo.
echo [%DATE% %TIME%] Servidor encerrado (errorlevel=%ERRORLEVEL%) >> "%LOGFILE%"
echo  =====================================================
echo  Servidor encerrado.
echo.
echo  Verifique o arquivo mpfm_inicio.log se houve erro.
echo.
echo  Pressione qualquer tecla para fechar...
pause >nul
endlocal
