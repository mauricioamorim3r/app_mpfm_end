#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para testar a inicialização
"""

import sys
import traceback

print("[1] Testando Python...", flush=True)
print(f"Python {sys.version}", flush=True)

try:
    print("[2] Importando app_config...", flush=True)
    from app_config import DEFAULT_PORT, DEFAULT_HOST
    print(f"✓ app_config OK - Port: {DEFAULT_PORT}, Host: {DEFAULT_HOST}", flush=True)
except Exception as e:
    print(f"✗ Erro em app_config: {e}", flush=True)
    traceback.print_exc()

try:
    print("[3] Importando FastAPI...", flush=True)
    from fastapi import FastAPI
    print("✓ FastAPI OK", flush=True)
except Exception as e:
    print(f"✗ Erro em FastAPI: {e}", flush=True)
    traceback.print_exc()

try:
    print("[4] Importando repositories...", flush=True)
    from repositories.cards import CardsRepository
    print("✓ repositories OK", flush=True)
except Exception as e:
    print(f"✗ Erro em repositories: {e}", flush=True)
    traceback.print_exc()

try:
    print("[5] Importando routes...", flush=True)
    from routes.cards_routes import register_cards_routes
    print("✓ routes OK", flush=True)
except Exception as e:
    print(f"✗ Erro em routes: {e}", flush=True)
    traceback.print_exc()

print("[✓] Diagnóstico Completo!", flush=True)
