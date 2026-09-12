@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo   XML 042 Multifasico - Gerador Standalone
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo ERRO: Python nao encontrado no PATH.
  echo Instale Python 3.10+ ou execute pelo terminal com o caminho completo.
  pause
  exit /b 1
)

echo Verificando dependencias...
python -c "import pandas, openpyxl" >nul 2>nul
if errorlevel 1 (
  echo Instalando dependencias locais do pacote...
  python -m pip install -r requirements_xml042_standalone.txt
  if errorlevel 1 (
    echo ERRO ao instalar dependencias.
    pause
    exit /b 1
  )
)

echo.
echo O script pedira o caminho do Excel Base_Unica OU da pasta onde ele esta.
echo Se for informada uma pasta, ele procura BASE_UNICA_TOTAL.xlsx automaticamente.
echo Se a Base_Unica falhar ou nao tiver candidatos, ele procura MPFM_MES_ANO.xlsx em data\outputs.
echo Os XMLs serao salvos em: %~dp0xml042_gerados
echo.
python gerar_xml042_standalone.py

echo.
pause
