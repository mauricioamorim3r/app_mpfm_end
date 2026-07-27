@echo off
REM Script de Inicializacao - MPFM Manager
REM Execute este arquivo APOS o administrador de TI conceder as permissoes

setlocal enabledelayedexpansion
title MPFM Manager - Bacalhau FPSO
color 0B

cd /d "%~dp0"

echo.
echo  =========================================
echo    MPFM MANAGER - Bacalhau FPSO
echo  =========================================
echo.
echo  Verificando Python...

REM Use Python do venv
set "PYTHON=.\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo  [ERRO] Python nao encontrado em %PYTHON%
    pause
    exit /b 1
)

echo  Python encontrado: %PYTHON%
echo.
echo  Iniciando servidor...
echo.

REM Define variaveis de ambiente
set "MPFM_PORT=8765"
set "MPFM_HOST=127.0.0.1"
set "MPFM_PUBLIC_BASE_URL=http://%MPFM_HOST%:%MPFM_PORT%"

REM Verifica se porta esta em uso
echo  Verificando porta %MPFM_PORT%...
netstat -ano | findstr ":%MPFM_PORT% " | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo  [AVISO] Porta %MPFM_PORT% ja esta em uso.
    echo  Encerrando o processo que usa essa porta...
    for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%MPFM_PORT% " ^| findstr "LISTENING"') do (
        echo  Parando PID %%P...
        taskkill /PID %%P /F >nul 2>&1
    )
    timeout /t 2 >nul
)

REM Executa servidor
"%PYTHON%" server.py

if errorlevel 1 (
    echo.
    echo  [ERRO] Falha ao executar server.py
    pause
    exit /b 1
)

exit /b 0
