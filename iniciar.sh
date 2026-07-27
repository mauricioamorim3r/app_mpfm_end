#!/bin/bash
# MPFM Manager — Script de inicialização Linux/Mac

echo ""
echo "  ========================================="
echo "    MPFM MANAGER — Bacalhau FPSO"
echo "  ========================================="
echo ""

# Verifica Python 3
if ! command -v python3 &>/dev/null; then
    echo "  [ERRO] Python3 não encontrado."
    echo "  Instale com: sudo apt install python3  (Linux)"
    echo "           ou: brew install python3      (Mac)"
    exit 1
fi

# Instala dependências
echo "  Verificando dependências..."
python3 -m pip install fastapi uvicorn python-multipart PyPDF2 pandas openpyxl numpy --quiet

echo ""
echo "  Iniciando servidor em http://localhost:8765"
echo "  Pressione Ctrl+C para parar."
echo ""

# Abre browser automaticamente
(sleep 2 && python3 -c "
import webbrowser, time
time.sleep(0.5)
webbrowser.open('http://localhost:8765')
" &)

# Inicia servidor
python3 server.py
