#!/usr/bin/env python3
"""
Detector de Proxy Corporativo - Windows
Descobre e testa configuracoes de proxy automaticamente
"""
import subprocess
import re
import os


def detectar_proxy_windows():
    """Detecta proxy configurado no Windows"""
    print("\n[*] Detectando configuracao de proxy do Windows...")

    try:
        # Executa comando netsh
        result = subprocess.run(
            ['netsh', 'winhttp', 'show', 'proxy'],
            capture_output=True,
            text=True,
            timeout=5
        )

        output = result.stdout
        print(output)

        # Procura por proxy na saída
        if 'Direct access' in output or 'Acesso direto' in output:
            print("[!] Nenhum proxy configurado no Windows")
            return None

        # Extrai URL do proxy
        proxy_match = re.search(r'Proxy Server\(s\)\s*:\s*([^\s]+)', output)
        if proxy_match:
            proxy = proxy_match.group(1)
            print(f"[OK] Proxy encontrado: {proxy}")
            return proxy

        return None

    except Exception as e:
        print(f"[ERRO] Nao foi possivel detectar: {e}")
        return None


def verificar_variaveis_ambiente():
    """Verifica variáveis de ambiente de proxy"""
    print("\n[*] Verificando variaveis de ambiente...")

    proxies = {}
    for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY']:
        val = os.environ.get(var)
        if val:
            proxies[var] = val
            print(f"    {var} = {val}")

    if not proxies:
        print("    Nenhuma variavel de proxy configurada")

    return proxies


def gerar_config_env(proxy_url):
    """Gera configuração para o .env"""
    print("\n" + "=" * 70)
    print("  CONFIGURACAO RECOMENDADA")
    print("=" * 70)
    print("\nAdicione estas linhas ao seu arquivo .env:\n")
    print(f"HTTP_PROXY={proxy_url}")
    print(f"HTTPS_PROXY={proxy_url}")
    print("NO_PROXY=localhost,127.0.0.1")
    print("\nDepois execute: python test_llm_quick.py")


def testar_conectividade_basica():
    """Testa conectividade básica"""
    print("\n[*] Testando conectividade basica...")

    sites = [
        ('Google', 'www.google.com'),
        ('DeepSeek', 'api.deepseek.com'),
        ('Kimi', 'api.moonshot.cn'),
    ]

    for nome, host in sites:
        try:
            result = subprocess.run(
                ['ping', '-n', '1', '-w', '1000', host],
                capture_output=True,
                timeout=3
            )
            if result.returncode == 0:
                print(f"    [OK] {nome:12} - Alcancavel")
            else:
                print(f"    [X]  {nome:12} - NAO alcancavel")
        except:
            print(f"    [?]  {nome:12} - Timeout")


if __name__ == "__main__":
    print("=" * 70)
    print("  DETECTOR DE PROXY - Equinor Network")
    print("=" * 70)

    # Detecta proxy
    proxy = detectar_proxy_windows()

    # Verifica variáveis
    env_proxies = verificar_variaveis_ambiente()

    # Testa conectividade
    testar_conectividade_basica()

    # Recomendações
    print("\n" + "=" * 70)
    print("  DIAGNOSTICO")
    print("=" * 70)

    if proxy:
        gerar_config_env(proxy)
    elif env_proxies:
        print("\n[OK] Proxies configurados nas variaveis de ambiente")
        print("     Se ainda nao funciona, o firewall pode estar bloqueando")
    else:
        print("\n[!] PROBLEMA: Rede corporativa sem proxy detectavel")
        print("\nSOLUCOES:")
        print("  1. Pergunte ao IT qual o proxy: suporte.ti@equinor.com")
        print("  2. Teste em outra rede (4G/casa)")
        print("  3. Solicite liberacao dos dominios:")
        print("     - api.deepseek.com")
        print("     - api.moonshot.cn")

    print("\n" + "=" * 70)
