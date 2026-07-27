@echo off
setlocal

rem registrar_autostart.bat
rem Coloca o VBS de inicializacao na pasta Startup do Windows.
rem O servidor MPFM Manager inicia automaticamente ao fazer login.
rem NAO requer permissao de Administrador.

set "VBS_SCRIPT=%~dp0start_server_hidden.vbs"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "DEST=%STARTUP_DIR%\MPFM_Manager_AutoStart.vbs"

if not exist "%VBS_SCRIPT%" (
    echo [ERRO] Script nao encontrado: %VBS_SCRIPT%
    pause
    exit /b 1
)

echo.
echo =========================================
echo   MPFM Manager - Registrar Autostart
echo =========================================
echo.
echo Origem: %VBS_SCRIPT%
echo Destino: %DEST%
echo.

copy /Y "%VBS_SCRIPT%" "%DEST%"

if errorlevel 1 (
    echo.
    echo [ERRO] Nao foi possivel copiar o arquivo para a pasta Startup.
    pause
    exit /b 1
)

echo.
echo  OK! Autostart registrado com sucesso.
echo.
echo  Na proxima vez que voce ligar o computador e entrar no Windows,
echo  o MPFM Manager vai iniciar automaticamente em segundo plano.
echo  O servidor estara disponivel em: http://localhost:8765
echo.
echo  Para remover o autostart no futuro, delete o arquivo:
echo    %DEST%
echo.
pause
