@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"
where python > nul 2> nul
if errorlevel 1 (
  echo ERRO: Python 3.10 ou superior nao foi encontrado.
  echo Instale Python e marque "Add Python to PATH".
  pause
  exit /b 1
)
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERRO: falha ao instalar dependencias.
  pause
  exit /b 1
)
echo.
echo Dependencias instaladas com sucesso.
echo Para PI Vision, instale tambem o navegador do Playwright quando solicitado pela equipe.
pause
endlocal
