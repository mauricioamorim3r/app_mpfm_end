@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo  Gerador Base_Unica Standalone - MPFM + SEP
echo ============================================================
echo.
echo Este modo interativo pedira os caminhos das pastas MPFM e SEP.
echo Para opcoes avancadas, leia README_BASE_UNICA_STANDALONE.md.
echo.
python gerar_base_unica_standalone.py
echo.
echo Execucao finalizada. Pressione qualquer tecla para sair.
pause > nul
endlocal
