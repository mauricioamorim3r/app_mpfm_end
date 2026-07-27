#!/usr/bin/env python3
"""
Teste com bypass SSL (APENAS PARA DIAGNÓSTICO)
AVISO: Desabilitar SSL é inseguro. Use apenas para testar conectividade.
"""
import os
import warnings
from openai import OpenAI
from dotenv import load_dotenv
import httpx

# Suprime avisos SSL (apenas para teste)
warnings.filterwarnings('ignore')
load_dotenv()


def test_with_proxy_detection():
    """Testa com detecção de proxy"""

    # Verifica proxies do sistema
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')

    print("\n[*] Configuração de Rede:")
    print(f"    HTTP_PROXY:  {http_proxy or 'Não configurado'}")
    print(f"    HTTPS_PROXY: {https_proxy or 'Não configurado'}")

    # Tenta DeepSeek com SSL desabilitado (APENAS TESTE)
    print("\n[*] Testando DeepSeek (SSL bypass)...")
    try:
        http_client = httpx.Client(verify=False, timeout=15.0)
        client = OpenAI(
            api_key=os.getenv('DEEPSEEK_API_KEY'),
            base_url='https://api.deepseek.com/v1',
            http_client=http_client
        )
        resp = client.chat.completions.create(
            model='deepseek-chat',
            messages=[{'role': 'user', 'content': 'Say: Test OK'}],
            max_tokens=10
        )
        print(f"[OK] DeepSeek respondeu: {resp.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"[ERRO] {type(e).__name__}: {str(e)[:150]}")
        return False


def test_kimi_bypass():
    """Testa Kimi com SSL bypass"""
    print("\n[*] Testando Kimi K3 (SSL bypass)...")
    try:
        http_client = httpx.Client(verify=False, timeout=15.0)
        client = OpenAI(
            api_key=os.getenv('KIMI_API_KEY'),
            base_url='https://api.moonshot.cn/v1',
            http_client=http_client
        )
        resp = client.chat.completions.create(
            model='moonshot-v1-8k',
            messages=[{'role': 'user', 'content': '说: 测试成功'}],
            max_tokens=10
        )
        print(f"[OK] Kimi respondeu: {resp.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"[ERRO] {type(e).__name__}: {str(e)[:150]}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("  TESTE DE DIAGNOSTICO - Bypass SSL")
    print("  AVISO: Este teste desabilita verificacao SSL (inseguro)")
    print("=" * 70)

    ds_ok = test_with_proxy_detection()
    km_ok = test_kimi_bypass()

    print("\n" + "=" * 70)
    print("  RESULTADO")
    print("=" * 70)
    print(f"DeepSeek: {'[OK]' if ds_ok else '[FALHOU]'}")
    print(f"Kimi K3:  {'[OK]' if km_ok else '[FALHOU]'}")

    if not (ds_ok or km_ok):
        print("\n[!] SOLUCOES POSSIVEIS:")
        print("    1. Configure proxy corporativo (veja proxy_config.txt)")
        print("    2. Use VPN se disponivel")
        print("    3. Solicite liberacao ao IT da Equinor")
        print("    4. Teste em outra rede (casa/4G)")
