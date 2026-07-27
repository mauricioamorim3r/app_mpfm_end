#!/usr/bin/env python3
"""
Teste Rapido - DeepSeek e Kimi K3
Uso: python test_llm_quick.py [deepseek|kimi|both]
"""
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def teste_rapido(provider: str):
    """Teste rapido de uma API"""
    if provider == "deepseek":
        key = os.getenv("DEEPSEEK_API_KEY", "")
        if "COLE_SUA" in key or not key:
            print("[ERRO] Configure DEEPSEEK_API_KEY no arquivo .env")
            return False

        print("\n[*] Testando DeepSeek...")
        try:
            client = OpenAI(
                api_key=key,
                base_url=os.getenv("DEEPSEEK_BASE_URL")
            )
            resp = client.chat.completions.create(
                model=os.getenv("DEEPSEEK_MODEL"),
                messages=[{"role": "user", "content": "Diga apenas 'OK'"}],
                max_tokens=5
            )
            print(f"[OK] DeepSeek: {resp.choices[0].message.content}")
            return True
        except Exception as e:
            print(f"[ERRO] DeepSeek falhou: {str(e)[:100]}")
            return False

    elif provider == "kimi":
        key = os.getenv("KIMI_API_KEY", "")
        if "COLE_SUA" in key or not key:
            print("[ERRO] Configure KIMI_API_KEY no arquivo .env")
            return False

        print("\n[*] Testando Kimi K3...")
        try:
            client = OpenAI(
                api_key=key,
                base_url=os.getenv("KIMI_BASE_URL")
            )
            resp = client.chat.completions.create(
                model=os.getenv("KIMI_MODEL"),
                messages=[{"role": "user", "content": "只说'好的'"}],
                max_tokens=5
            )
            print(f"[OK] Kimi K3: {resp.choices[0].message.content}")
            return True
        except Exception as e:
            print(f"[ERRO] Kimi falhou: {str(e)[:100]}")
            return False


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "both"

    print("=" * 60)
    print("  Teste Rapido - LLMs")
    print("=" * 60)

    if target in ["deepseek", "both"]:
        teste_rapido("deepseek")

    if target in ["kimi", "both"]:
        teste_rapido("kimi")

    print("\n" + "=" * 60)
