#!/usr/bin/env python3
"""
Configurador de APIs DeepSeek e Kimi K3
Execute: python setup_llms.py
"""
import os
from pathlib import Path

def adicionar_ao_env(chaves: dict):
    """Adiciona as chaves de API ao arquivo .env"""
    env_path = Path(".env")

    # Lê o conteúdo atual
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            linhas = f.readlines()
    else:
        linhas = []

    # Remove linhas antigas das mesmas keys
    linhas_novas = [l for l in linhas if not any(k in l for k in chaves.keys())]

    # Adiciona as novas chaves
    linhas_novas.append("\n# === DeepSeek e Kimi APIs ===\n")
    for key, value in chaves.items():
        linhas_novas.append(f"{key}={value}\n")

    # Salva
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(linhas_novas)

    print(f"[OK] Configuracoes salvas em {env_path.absolute()}")


def main():
    print("=" * 60)
    print("  Configurador DeepSeek + Kimi K3")
    print("=" * 60)

    # Solicita as API keys
    print("\n[*] Cole suas API keys (ou deixe em branco para pular):\n")

    deepseek_key = input("DeepSeek API Key: ").strip()
    kimi_key = input("Kimi K3 API Key: ").strip()

    chaves = {}

    if deepseek_key:
        chaves["DEEPSEEK_API_KEY"] = deepseek_key
        chaves["DEEPSEEK_MODEL"] = "deepseek-chat"
        chaves["DEEPSEEK_BASE_URL"] = "https://api.deepseek.com/v1"

    if kimi_key:
        chaves["KIMI_API_KEY"] = kimi_key
        chaves["KIMI_MODEL"] = "moonshot-v1-8k"
        chaves["KIMI_BASE_URL"] = "https://api.moonshot.cn/v1"

    if not chaves:
        print("\n[!] Nenhuma chave fornecida. Configure manualmente no .env")
        return

    # Adiciona ao .env
    adicionar_ao_env(chaves)

    print("\n" + "=" * 60)
    print("  [OK] Configuracao Concluida!")
    print("=" * 60)
    print("\nProximo passo: Execute 'python test_llms.py' para testar")


if __name__ == "__main__":
    main()
