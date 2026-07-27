#!/bin/bash
# Azure App Service startup command
# Configurar em: App Service → Configuration → General Settings → Startup Command
# Valor: bash startup.sh

mkdir -p /data/uploads /data/outputs
exec python server.py
