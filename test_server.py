#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste estendido - Tentando iniciar o servidor
"""

import sys
import traceback
import time

print("[START] Iniciando teste estendido...", flush=True)

try:
    print("[1] Criando app FastAPI...", flush=True)
    from fastapi import FastAPI
    from app_config import APP_TITLE, APP_VERSION, DEFAULT_HOST, DEFAULT_PORT
    
    app = FastAPI(title=APP_TITLE, version=APP_VERSION)
    print("✓ FastAPI app criado", flush=True)
    
    print("[2] Adicionando rota de teste...", flush=True)
    @app.get("/test")
    def test_route():
        return {"status": "ok"}
    
    print("✓ Rota de teste adicionada", flush=True)
    
    print(f"\n[✓] SUCESSO! Servidor pronto para iniciar")
    print(f"    Acesse: http://{DEFAULT_HOST}:{DEFAULT_PORT}")
    print(f"    Swagger UI: http://127.0.0.1:{DEFAULT_PORT}/docs")
    
    # Aguarda input do usuário antes de iniciar (deixe como fallback)
    print("\n[INFO] Pressione Enter para iniciar o servidor ou Ctrl+C para cancelar...")
    sys.stdout.flush()
    input()
    
    print("\n[3] Iniciando uvicorn...", flush=True)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=DEFAULT_PORT, log_level="info")
    
except KeyboardInterrupt:
    print("\n[CANCELADO] Execução interrompida pelo usuário", flush=True)
    sys.exit(0)
except Exception as e:
    print(f"\n✗ ERRO: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
