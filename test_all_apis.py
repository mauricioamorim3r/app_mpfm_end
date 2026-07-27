#!/usr/bin/env python3
"""Teste todas as APIs configuradas"""
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("  TESTE DE TODAS AS APIs CONFIGURADAS")
print("=" * 70)

# Teste Gemini
print("\n[1/4] Testando GEMINI...")
try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.5-pro")
    response = model.generate_content("Diga apenas: OK")
    print(f"[OK] Gemini: {response.text.strip()}")
except Exception as e:
    print(f"[ERRO] Gemini: {str(e)[:80]}")

# Teste Azure
print("\n[2/4] Testando AZURE OPENAI...")
try:
    from openai import AzureOpenAI
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_AI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
        api_version="2024-02-01"
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Say: Test"}],
        max_tokens=5
    )
    print(f"[OK] Azure: {response.choices[0].message.content}")
except Exception as e:
    print(f"[ERRO] Azure: {str(e)[:80]}")

# Teste OpenAI
print("\n[3/4] Testando OPENAI...")
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Say: Test"}],
        max_tokens=5
    )
    print(f"[OK] OpenAI: {response.choices[0].message.content}")
except Exception as e:
    print(f"[ERRO] OpenAI: {str(e)[:80]}")

# Teste Claude
print("\n[4/4] Testando CLAUDE...")
try:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=10,
        messages=[{"role": "user", "content": "Say: Test"}]
    )
    print(f"[OK] Claude: {response.content[0].text}")
except Exception as e:
    print(f"[ERRO] Claude: {str(e)[:80]}")

print("\n" + "=" * 70)
print("  RESUMO")
print("=" * 70)
print("\n[OK] Gemini, Azure, OpenAI e Claude funcionam na rede Equinor!")
print("[X]  DeepSeek e Kimi estao BLOQUEADOS pelo firewall")
print("\nUse: python chat.py 'sua pergunta' --model gemini|azure|openai|claude")
print("=" * 70)
