#!/usr/bin/env python3
"""
Wrapper unificado para usar todas as LLMs configuradas
Uso: python llm.py "sua pergunta aqui" [--model deepseek|kimi|gemini|openai|claude]
"""
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def chat(prompt: str, model: str = "deepseek") -> str:
    """Envia uma mensagem para o modelo especificado"""

    if model == "deepseek":
        key = os.getenv("DEEPSEEK_API_KEY", "")
        if "COLE_SUA" in key or not key:
            return "[ERRO] Configure DEEPSEEK_API_KEY no .env"

        client = OpenAI(
            api_key=key,
            base_url=os.getenv("DEEPSEEK_BASE_URL")
        )
        resp = client.chat.completions.create(
            model=os.getenv("DEEPSEEK_MODEL"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return resp.choices[0].message.content

    elif model == "kimi":
        key = os.getenv("KIMI_API_KEY", "")
        if "COLE_SUA" in key or not key:
            return "[ERRO] Configure KIMI_API_KEY no .env"

        client = OpenAI(
            api_key=key,
            base_url=os.getenv("KIMI_BASE_URL")
        )
        resp = client.chat.completions.create(
            model=os.getenv("KIMI_MODEL"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return resp.choices[0].message.content

    elif model == "openai":
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content

    else:
        return f"[ERRO] Modelo '{model}' nao suportado. Use: deepseek, kimi, openai"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python llm.py 'sua pergunta' [--model deepseek|kimi|openai]")
        sys.exit(1)

    # Parse argumentos
    pergunta = sys.argv[1]
    modelo = "deepseek"  # padrão

    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            modelo = sys.argv[idx + 1]

    print(f"\n[{modelo.upper()}]")
    print("=" * 60)

    resposta = chat(pergunta, modelo)
    print(resposta)
    print("=" * 60 + "\n")
