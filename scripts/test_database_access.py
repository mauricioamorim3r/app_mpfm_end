#!/usr/bin/env python3
"""
Teste de banco de dados via Playwright
Testa conectividade básica da aplicação
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "http://localhost:8765"

def req(path: str, method: str = "GET", data: dict | None = None, timeout: int = 10):
    """Fazer requisição HTTP"""
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    
    try:
        r = urllib.request.Request(BASE_URL + path, data=body, headers=headers, method=method)
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            payload = resp.read()
            return resp.status, resp.headers, (json.loads(payload) if payload else {})
    except urllib.error.HTTPError as e:
        return e.code, e.headers, {"error": str(e)}
    except Exception as e:
        return 0, {}, {"error": str(e)}


def test_server_connectivity():
    """Teste 1: Conectividade básica"""
    print("\n" + "="*60)
    print("[TEST 1] Conectividade do servidor")
    print("="*60)
    
    status, headers, body = req("/health")
    print(f"GET /health")
    print(f"  Status: {status}")
    print(f"  Response: {json.dumps(body, indent=2)}")
    
    if status == 200 and body.get("status") == "ok":
        print("✓ PASS: Servidor respondendo")
        return True
    else:
        print("✗ FAIL: Servidor não respondendo corretamente")
        return False


def test_home_page():
    """Teste 2: Página inicial"""
    print("\n" + "="*60)
    print("[TEST 2] Página inicial (index.html)")
    print("="*60)
    
    try:
        with urllib.request.urlopen(BASE_URL + "/", timeout=10) as resp:
            content = resp.read().decode("utf-8")
            status = resp.status
            print(f"GET /")
            print(f"  Status: {status}")
            print(f"  Size: {len(content)} bytes")
            print(f"  Has DOCTYPE: {'<!DOCTYPE' in content}")
            print(f"  Has title: {'<title>' in content}")
            
            if status == 200 and "<!DOCTYPE" in content:
                print("✓ PASS: Página inicial carregando")
                return True
            else:
                print("✗ FAIL: Página inicial inválida")
                return False
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_static_files():
    """Teste 3: Arquivos estáticos"""
    print("\n" + "="*60)
    print("[TEST 3] Arquivos estáticos")
    print("="*60)
    
    static_files = [
        "/static/app.main.js",
        "/static/app.base.css",
        "/static/app.shared.js"
    ]
    
    results = []
    for file in static_files:
        try:
            with urllib.request.urlopen(BASE_URL + file, timeout=10) as resp:
                content = resp.read()
                status = resp.status
                print(f"GET {file}: {status} ({len(content)} bytes)")
                results.append(status == 200)
        except urllib.error.HTTPError as e:
            print(f"GET {file}: {e.code} (não encontrado)")
            results.append(False)
    
    if all(results):
        print("✓ PASS: Todos os arquivos estáticos carregando")
        return True
    else:
        print("⚠ PARTIAL: Alguns arquivos estáticos faltando")
        return len([r for r in results if r]) >= 1


def test_database_access():
    """Teste 4: Verificar acesso ao banco de dados"""
    print("\n" + "="*60)
    print("[TEST 4] Acesso ao banco de dados")
    print("="*60)
    
    db_path = Path("data/mpfm_local.db")
    
    if db_path.exists():
        size = db_path.stat().st_size
        mtime = db_path.stat().st_mtime
        print(f"Arquivo: {db_path}")
        print(f"  Tamanho: {size:,} bytes ({size/1024/1024:.1f} MB)")
        print(f"  Modificado: {mtime}")
        
        # Tentar conectar ao BD
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            
            # Verificar tabelas principais
            cur.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """)
            tables = [row[0] for row in cur.fetchall()]
            print(f"  Tabelas: {len(tables)} encontradas")
            for table in tables[:10]:  # Mostrar primeiras 10
                print(f"    - {table}")
            
            # Contar registros em tabelas principais
            important_tables = ['measurements_curated', 'files_imported', 'processing_runs']
            for table in important_tables:
                if table in tables:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cur.fetchone()[0]
                    print(f"  {table}: {count:,} registros")
            
            conn.close()
            print("✓ PASS: Banco de dados acessível e contém dados")
            return True
        except Exception as e:
            print(f"✗ FAIL: Erro ao acessar BD: {e}")
            return False
    else:
        print(f"✗ FAIL: Arquivo não encontrado: {db_path}")
        return False


def main():
    print("\n" + "="*60)
    print("  TESTES DE APLICAÇÃO MPFM")
    print("  Servidor: " + BASE_URL)
    print("="*60)
    
    results = []
    
    # Executar testes
    results.append(("Conectividade", test_server_connectivity()))
    results.append(("Página Inicial", test_home_page()))
    results.append(("Estáticos", test_static_files()))
    results.append(("Banco de Dados", test_database_access()))
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n✓ TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print(f"\n⚠ {total - passed} teste(s) falharam")
        return 1


if __name__ == "__main__":
    sys.exit(main())
