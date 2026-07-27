#!/usr/bin/env python3
"""
Wrapper Universal LLM - Usa todas as suas APIs disponiveis
Suporta: Gemini, Azure OpenAI, OpenAI, Anthropic Claude
"""
import os
from dotenv import load_dotenv

load_dotenv()


def chat(prompt: str, provider: str = "gemini") -> str:
    """Envia prompt para o provider especificado"""

    if provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-pro"))
        response = model.generate_content(prompt)
        return response.text

    elif provider == "azure":
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_AI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
            api_version="2024-02-01"
        )
        response = client.chat.completions.create(
            model=os.getenv("AZURE_AI_MODEL", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    elif provider == "claude":
        from anthropic import Anthropic
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    else:
        return f"[ERRO] Provider '{provider}' invalido. Use: gemini, azure, openai, claude"


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python chat.py 'sua pergunta' [--model gemini|azure|openai|claude]")
        print("\nModelos disponiveis:")
        print("  - gemini  : Google Gemini 2.5 Pro")
        print("  - azure   : Azure GPT-4o")
        print("  - openai  : OpenAI GPT-4o")
        print("  - claude  : Anthropic Claude 3.5 Sonnet")
        sys.exit(1)

    pergunta = sys.argv[1]
    modelo = "gemini"  # padrão

    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            modelo = sys.argv[idx + 1]

    print(f"\n[{modelo.upper()}]")
    print("=" * 70)

    try:
        resposta = chat(pergunta, modelo)
        print(resposta)
    except Exception as e:
        print(f"[ERRO] {e}")

    print("=" * 70 + "\n")
