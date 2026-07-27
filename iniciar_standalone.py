"""
MPFM Manager — Launcher Standalone (modo rede)
Uso: python iniciar_standalone.py
     python iniciar_standalone.py --local   (apenas esta maquina)
Nao requer VS Code, nao requer admin.
"""
import os
import sys
import socket
import threading
import time
import webbrowser

# ── Configuracao ─────────────────────────────────────────────────────────────
PORT = 8765
MODO_LOCAL = "--local" in sys.argv


def get_local_ip() -> str:
    """Descobre o IP de rede desta maquina (evita 127.x e 169.x)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"


def abrir_browser(url: str, delay: float = 2.5) -> None:
    time.sleep(delay)
    webbrowser.open(url)


def main() -> None:
    # Garante que o diretorio de trabalho seja a pasta do script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    if MODO_LOCAL:
        host = "127.0.0.1"
        ip = "127.0.0.1"
    else:
        host = "0.0.0.0"
        ip = get_local_ip()

    local_url  = f"http://127.0.0.1:{PORT}"
    public_url = f"http://{ip}:{PORT}"

    # Define variaveis de ambiente antes de importar server
    os.environ["MPFM_HOST"]            = host
    os.environ["MPFM_PORT"]            = str(PORT)
    os.environ["MPFM_PUBLIC_BASE_URL"] = public_url

    print("=" * 54)
    print("  MPFM MANAGER — Inicializando...")
    print("=" * 54)
    if MODO_LOCAL:
        print(f"  Modo:               Local (somente esta maquina)")
        print(f"  Acesso:             {local_url}")
    else:
        print(f"  Modo:               Rede")
        print(f"  Esta maquina:       {local_url}")
        print(f"  Outros computadores: {public_url}")
    print("-" * 54)
    print("  Pressione Ctrl+C para encerrar o servidor")
    print("=" * 54)
    print()

    # Abre navegador em segundo plano apos o servidor estar pronto
    threading.Thread(target=abrir_browser, args=(local_url,), daemon=True).start()

    # Inicia uvicorn diretamente (nao via server.py __main__)
    try:
        import uvicorn
    except ImportError:
        print("[INFO] uvicorn nao encontrado. Instalando dependencias (sem admin)...")
        import subprocess
        req = os.path.join(base_dir, "requirements.txt")
        if os.path.exists(req):
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "-r", req])
        else:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user",
                                   "uvicorn", "fastapi", "python-multipart",
                                   "pypdf", "pandas", "openpyxl", "numpy"])
        import uvicorn

    try:
        uvicorn.run(
            "server:app",
            host=host,
            port=PORT,
            reload=False,
            use_colors=False,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\n[INFO] Servidor encerrado pelo usuario.")
    except Exception as e:
        print(f"\n[ERRO] Falha ao iniciar servidor: {e}")
        input("Pressione Enter para fechar...")


if __name__ == "__main__":
    main()
