@echo off
REM ============================================================================
REM Script para executar a automacao de download de emails DPB
REM Pode ser executado com duplo clique no Windows Explorer
REM 
REM Funcionalidades:
REM - Baixa ZIPs de Daily Reports, Configuration e FCVs do email
REM - Descompacta automaticamente nas pastas de ano/mes
REM - Organiza arquivos .txt orfaos quando pasta do dia e criada
REM - Move ZIPs processados para pasta de Registros
REM - Controle de duplicados via JSON
REM ============================================================================

echo.
echo ================================================================================
echo DPB FPSO BACALHAU - AUTOMACAO DE DOWNLOAD DE EMAILS
echo ================================================================================
echo.
echo Iniciando automacao...
echo.

REM Navegar para a pasta do script
cd /d "%~dp0"

REM Executar o script Python
python baixar_zip_email.py

echo.
echo ================================================================================
echo AUTOMACAO FINALIZADA
echo ================================================================================
echo.
echo Pressione qualquer tecla para fechar esta janela...
pause >nul
