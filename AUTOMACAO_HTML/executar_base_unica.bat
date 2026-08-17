@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"
where python > nul 2> nul
if errorlevel 1 (
  echo ERRO: Python 3.10 ou superior nao foi encontrado.
  pause
  exit /b 1
)
echo ============================================================
echo   Automacao Base_Unica - pacote distribuivel
 echo ============================================================
echo.
echo O modo assistido solicitara os caminhos e a janela de analise.
echo Para uso inicial sem PI Vision, escolha o modo 7 e use --no-pi quando necessario.
echo.
python gerar_base_unica_standalone.py --ask-period
set "RC=%errorlevel%"
echo.
echo Execucao finalizada com codigo %RC%.
pause
endlocal & exit /b %RC%
