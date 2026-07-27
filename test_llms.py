#!/usr/bin/env python3
"""
Testador de APIs DeepSeek e Kimi K3
Execute: python test_llms.py
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()


def testar_deepseek():
    """Testa a API DeepSeek"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("[!] DEEPSEEK_API_KEY nao encontrada no .env")
        return False

    try:
        print("\n[*] Testando DeepSeek...")
        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        )

        response = client.chat.completions.create(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            messages=[
                {"role": "system", "content": "Você é um assistente útil."},
                {"role": "user", "content": "Diga 'Olá' em uma palavra apenas."}
            ],
            max_tokens=10
        )

        resultado = response.choices[0].message.content
        print(f"[OK] DeepSeek respondeu: {resultado}")
        return True

    except Exception as e:
        print(f"[ERRO] Erro no DeepSeek: {e}")
        return False


def testar_kimi():
    """Testa a API Kimi K3"""
    api_key = os.getenv("KIMI_API_KEY")
    if not api_key:
        print("[!] KIMI_API_KEY nao encontrada no .env")
        return False

    try:
        print("\n[*] Testando Kimi K3...")
        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
        )

        response = client.chat.completions.create(
            model=os.getenv("KIMI_MODEL", "moonshot-v1-8k"),
            messages=[
                {"role": "system", "content": "你是一个有帮助的助手。"},
                {"role": "user", "content": "用一个词说'你好'"}
            ],
            max_tokens=10
        )

        resultado = response.choices[0].message.content
        print(f"[OK] Kimi K3 respondeu: {resultado}")
        return True

    except Exception as e:
        print(f"[ERRO] Erro no Kimi K3: {e}")
        return False


def exemplo_uso():
    """Mostra exemplo de uso simples"""
    print("\n" + "=" * 60)
    print("  [*] Exemplo de Uso em Python")
    print("=" * 60)
    print("""
from openai import OpenAI
import os

# Para DeepSeek:
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "Olá!"}]
)
print(response.choices[0].message.content)

# Para Kimi K3:
client = OpenAI(
    api_key=os.getenv("KIMI_API_KEY"),
    base_url="https://api.moonshot.cn/v1"
)

response = client.chat.completions.create(
    model="moonshot-v1-8k",
    messages=[{"role": "user", "content": "你好!"}]
)
print(response.choices[0].message.content)
""")


def main():
    print("=" * 60)
    print("  Testador DeepSeek + Kimi K3")
    print("=" * 60)

    # Testa as APIs
    deepseek_ok = testar_deepseek()
    kimi_ok = testar_kimi()

    # Resumo
    print("\n" + "=" * 60)
    print("  [*] Resumo dos Testes")
    print("=" * 60)
    print(f"DeepSeek: {'[OK]' if deepseek_ok else '[ERRO]'}")
    print(f"Kimi K3:  {'[OK]' if kimi_ok else '[ERRO]'}")

    if deepseek_ok or kimi_ok:
        exemplo_uso()


if __name__ == "__main__":
    main()
