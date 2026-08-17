"""
Script de manutencao do banco MPFM.
Deve ser executado com o servidor PARADO para evitar locks.

Fluxo:
1. Faz backup do banco atual
2. Executa VACUUM para reduzir fragmentacao
3. Verifica integridade
4. Substitui o banco original pelo otimizado
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/mpfm_local.db")
VACUUM_PATH = Path("data/mpfm_local_vacuum.db")


def main():
    if not DB_PATH.exists():
        print(f"Banco nao encontrado: {DB_PATH}")
        sys.exit(1)

    original_size = DB_PATH.stat().st_size
    print(f"Tamanho original: {original_size / 1024 / 1024:.1f} MB")

    # Backup de seguranca
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(f"data/backups/mpfm_before_vacuum_{ts}.db")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB_PATH, backup_path)
    print(f"Backup criado: {backup_path}")

    # Remove copia anterior de vacuum se existir
    if VACUUM_PATH.exists():
        VACUUM_PATH.unlink()

    try:
        src = sqlite3.connect(str(DB_PATH), timeout=5)
        dst = sqlite3.connect(str(VACUUM_PATH), timeout=5)
        print("Copiando banco para arquivo temporario...")
        src.backup(dst)
        src.close()
        dst.close()

        print("Executando VACUUM...")
        conn = sqlite3.connect(str(VACUUM_PATH), timeout=30)
        conn.execute("PRAGMA cache_size = -64000")
        conn.execute("VACUUM")

        print("Verificando integridade...")
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        conn.close()

        if result != "ok":
            print(f"FALHA na integridade apos VACUUM: {result}")
            sys.exit(1)

        vacuum_size = VACUUM_PATH.stat().st_size
        print(f"Tamanho apos VACUUM: {vacuum_size / 1024 / 1024:.1f} MB")
        saved = original_size - vacuum_size
        print(f"Espaco economizado: {saved / 1024 / 1024:.1f} MB ({saved / original_size * 100:.1f}%)")

        # Substitui o banco original
        print("Substituindo banco original pelo otimizado...")
        shutil.move(str(VACUUM_PATH), str(DB_PATH))
        print("Concluido. O banco foi otimizado com sucesso.")

    except sqlite3.OperationalError as e:
        print(f"ERRO: {e}")
        print("Provavelmente o servidor esta rodando e segurando o banco.")
        print("Pare o servidor e execute este script novamente.")
        if VACUUM_PATH.exists():
            VACUUM_PATH.unlink()
        sys.exit(1)
    except Exception as e:
        print(f"ERRO inesperado: {e}")
        if VACUUM_PATH.exists():
            VACUUM_PATH.unlink()
        sys.exit(1)


if __name__ == "__main__":
    main()
