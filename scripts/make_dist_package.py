"""
make_dist_package.py
====================
Gera um pacote ZIP de distribuição da aplicação MPFM pronto para outro usuário.

O que inclui:
  - Código completo (routes/, services/, repositories/, static/, templates/,
    scripts/, alarme/, design-system/, docs/)
  - Arquivos raiz (.py, .html, .json, .bat, .sh, .ps1, .md, .txt)
  - data/mpfm_local.db  (banco populado com os dados curados)
  - data/cadastro.json
  - data/outputs/*.xlsx (apenas workbooks principais, sem temporários -lt-)
  - data/user_prefs.json SANITIZADO (folders monitorados removidos — paths
    são específicos de cada máquina)

O que NÃO inclui:
  - old/              (backups de código)
  - data/uploads/     (arquivos temporários de upload)
  - data/outputs/MPFM_backup_*.zip
  - data/outputs/*-lt-*.xlsx  (workbooks temporários de reconstrução)
  - data/_monthly_refresh/
  - __pycache__/
  - *.pyc / *.pyo
  - .git/

Uso:
  python scripts/make_dist_package.py

O arquivo gerado será salvo na pasta pai da aplicação:
  ../MPFM_DIST_<data>.zip
"""

import os
import zipfile
import json
import shutil
import datetime
import sys
import fnmatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ─── Pastas/arquivos a INCLUIR explicitamente ────────────────────────────────
INCLUDE_DIRS = [
    "routes",
    "services",
    "repositories",
    "static",
    "templates",
    "scripts",
    "alarme",
    "design-system",
    "docs",
]

INCLUDE_ROOT_EXTS = {".py", ".html", ".json", ".bat", ".sh", ".ps1", ".md", ".txt"}
INCLUDE_ROOT_FILES_EXPLICIT = {
    "app_config.py", "db_schema.py", "mpfm_engine.py", "recon_engine.py",
    "server.py", "import_recent_reports.py",
    "index.html",
    "iniciar.bat", "iniciar.sh", "iniciar_simples.bat", "start_app.ps1", "iniciar_com_shell.ps1",
    "README.md", "README_EXECUCAO.txt", "EXECUTION_GUIDE.md",
}

# ─── Patterns a EXCLUIR (globais) ────────────────────────────────────────────
EXCLUDE_DIRS  = {"old", "__pycache__", ".git", ".vscode", "node_modules"}
EXCLUDE_FILES = {
    # padrões por sufixo / prefixo
    "*.pyc", "*.pyo",
    ".tmp_*",
    "diag*.py",
}

# ─── Arquivos data/ a incluir ────────────────────────────────────────────────
DATA_DB          = os.path.join(ROOT, "data", "mpfm_local.db")
DATA_CADASTRO    = os.path.join(ROOT, "data", "cadastro.json")

# Workbooks: só os principais (sem -lt- e sem backups .zip)
def _is_main_workbook(name: str) -> bool:
    if name.endswith(".zip"):
        return False
    if "-lt-" in name:
        return False
    if name.endswith(".xlsx"):
        return True
    return False

OUTPUTS_DIR = os.path.join(ROOT, "data", "outputs")


def _sanitize_prefs(src_path: str) -> bytes:
    """
    Lê user_prefs.json e retorna versão sanitizada:
    - Remove os folders monitorados (paths específicos de cada máquina)
    - Mantém configurações gerais (tema, horários, xml042_cnpj8, etc.)
    """
    with open(src_path, encoding="utf-8") as f:
        prefs = json.load(f)

    afm = prefs.get("auto_folder_monitor", {})
    afm["folders"] = []   # limpa paths da máquina origem
    afm["enabled"] = False  # desliga monitor até o novo usuário configurar
    prefs["auto_folder_monitor"] = afm

    # Remove sentinela de teste se houver
    prefs.pop("__test_sentinel", None)

    return json.dumps(prefs, ensure_ascii=False, indent=2).encode("utf-8")


def _should_skip_file(rel_path: str) -> bool:
    parts = rel_path.replace("\\", "/").split("/")
    # Exclui pastas raiz bloqueadas
    if parts[0] in EXCLUDE_DIRS:
        return True
    for part in parts:
        if part in {"__pycache__", ".git", "node_modules"}:
            return True
    name = parts[-1]
    if name.endswith((".pyc", ".pyo")):
        return True
    if any(fnmatch.fnmatch(name, pattern) for pattern in EXCLUDE_FILES):
        return True
    return False


def build_package() -> str:
    date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    dist_name = f"MPFM_DIST_{date_str}.zip"
    dist_path = os.path.join(os.path.dirname(ROOT), dist_name)

    print(f"\n{'═'*60}")
    print(f"  Gerando pacote de distribuição MPFM")
    print(f"  Destino: {dist_path}")
    print(f"{'═'*60}\n")

    total_files = 0
    total_bytes = 0

    with zipfile.ZipFile(dist_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:

        # ── 1. Código raiz ────────────────────────────────────────────────
        print("[ 1/5 ] Arquivos raiz...")
        for name in os.listdir(ROOT):
            fpath = os.path.join(ROOT, name)
            if not os.path.isfile(fpath):
                continue
            if name == "COMO_USAR.txt":
                continue
            _, ext = os.path.splitext(name)
            if name in INCLUDE_ROOT_FILES_EXPLICIT or ext in INCLUDE_ROOT_EXTS:
                if _should_skip_file(name):
                    continue
                zf.write(fpath, arcname=name)
                total_files += 1
                total_bytes += os.path.getsize(fpath)
                print(f"    + {name}")

        # ── 2. Pastas de código ───────────────────────────────────────────
        print(f"\n[ 2/5 ] Pastas de código {INCLUDE_DIRS}...")
        for d in INCLUDE_DIRS:
            dir_path = os.path.join(ROOT, d)
            if not os.path.isdir(dir_path):
                print(f"    ⚠  {d}/ não encontrada — ignorando")
                continue
            count = 0
            for dirpath, dirnames, filenames in os.walk(dir_path):
                # Poda pastas excluídas in-place
                dirnames[:] = [x for x in dirnames if x not in EXCLUDE_DIRS]
                for filename in filenames:
                    fpath = os.path.join(dirpath, filename)
                    rel = os.path.relpath(fpath, ROOT)
                    if _should_skip_file(rel):
                        continue
                    zf.write(fpath, arcname=rel)
                    total_files += 1
                    total_bytes += os.path.getsize(fpath)
                    count += 1
            print(f"    + {d}/  ({count} arquivos)")

        # ── 3. Banco de dados ─────────────────────────────────────────────
        print(f"\n[ 3/5 ] Banco de dados...")
        if os.path.exists(DATA_DB):
            sz = os.path.getsize(DATA_DB) / 1024 / 1024
            print(f"    + data/mpfm_local.db  ({sz:.1f} MB) — pode demorar...")
            zf.write(DATA_DB, arcname="data/mpfm_local.db")
            total_files += 1
            total_bytes += os.path.getsize(DATA_DB)
        else:
            print("    ⚠  mpfm_local.db não encontrado")

        if os.path.exists(DATA_CADASTRO):
            zf.write(DATA_CADASTRO, arcname="data/cadastro.json")
            total_files += 1
            total_bytes += os.path.getsize(DATA_CADASTRO)
            print("    + data/cadastro.json")

        # ── 4. user_prefs.json sanitizado ─────────────────────────────────
        print(f"\n[ 4/5 ] user_prefs.json (sanitizado)...")
        prefs_src = os.path.join(ROOT, "data", "user_prefs.json")
        if os.path.exists(prefs_src):
            sanitized = _sanitize_prefs(prefs_src)
            zf.writestr("data/user_prefs.json", sanitized)
            total_files += 1
            total_bytes += len(sanitized)
            print("    + data/user_prefs.json  (folders monitorados removidos)")

        # ── 5. Workbooks Excel ────────────────────────────────────────────
        print(f"\n[ 5/5 ] Workbooks Excel...")
        if os.path.isdir(OUTPUTS_DIR):
            wb_count = 0
            for name in sorted(os.listdir(OUTPUTS_DIR)):
                if _is_main_workbook(name):
                    fpath = os.path.join(OUTPUTS_DIR, name)
                    sz_kb = os.path.getsize(fpath) / 1024
                    zf.write(fpath, arcname=f"data/outputs/{name}")
                    total_files += 1
                    total_bytes += os.path.getsize(fpath)
                    print(f"    + data/outputs/{name}  ({sz_kb:.0f} KB)")
                    wb_count += 1
            if wb_count == 0:
                print("    ⚠  nenhum workbook principal encontrado")

        # ── Instrução de uso embutida no ZIP ──────────────────────────────
        readme = _make_readme()
        zf.writestr("COMO_USAR.txt", readme.encode("utf-8"))

    zip_size = os.path.getsize(dist_path) / 1024 / 1024
    print(f"\n{'═'*60}")
    print(f"  ✓  Pacote gerado com sucesso!")
    print(f"  Arquivos incluídos: {total_files:,}")
    print(f"  Dados originais:    {total_bytes/1024/1024:.1f} MB")
    print(f"  Tamanho do ZIP:     {zip_size:.1f} MB")
    print(f"  Arquivo:            {dist_path}")
    print(f"{'═'*60}\n")
    return dist_path


def _make_readme() -> str:
    return """\
========================================
  MPFM Manager — Pacote de Distribuição
========================================

PRÉ-REQUISITOS
--------------
- Python 3.11 ou superior
- Bibliotecas listadas em requirements.txt (se existir)
  ou instale manualmente:
    pip install fastapi uvicorn openpyxl pdfplumber sqlalchemy

INSTALAÇÃO
----------
1. Extraia o conteúdo desta pasta para um local de sua escolha.
   Exemplo: C:\\Users\\SEU_USUARIO\\MPFM_APP\\

2. Abra um terminal na pasta extraída e instale dependências:
     pip install fastapi uvicorn openpyxl pdfplumber sqlalchemy python-multipart aiofiles

INICIAR A APLICAÇÃO
-------------------
Opção A (Windows — duplo clique):
  iniciar_simples.bat

Opção B (terminal):
  python server.py

Opção C (PowerShell):
  .\\start_app.ps1

Acesse no navegador:  http://localhost:8765

BANCO DE DADOS
--------------
O arquivo data/mpfm_local.db já contém todos os dados importados
(medições Oct/2025 → Abr/2026, ~642k linhas curadas).

CONFIGURAR PASTAS MONITORADAS
------------------------------
As pastas de monitoramento automático (PDFs diários) foram removidas
pois são específicas de cada máquina. Para reconfigurar:
  1. Acesse a aplicação em http://localhost:8765
  2. Vá em "Upload / Importação" → seção "Monitor Automático de Pasta"
  3. Adicione os caminhos das suas pastas de PDFs MPFM

ARQUIVOS EXCEL
--------------
Os workbooks mensais estão disponíveis em data/outputs/ e também
podem ser acessados/baixados pela interface em "Exportar".

========================================
"""


if __name__ == "__main__":
    build_package()
