from __future__ import annotations

import datetime as dt
import fnmatch
import json
import os
import shutil
import sqlite3
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "build" / "release"

SOURCE_DIRS = [
    "repositories",
    "routes",
    "scripts",
    "services",
    "static",
    "templates",
    "docs",
    "design-system",
]

ROOT_FILES = [
    "app_config.py",
    "db_schema.py",
    "import_recent_reports.py",
    "index.html",
    "iniciar.bat",
    "iniciar.sh",
    "iniciar_simples.bat",
    "iniciar_rede.bat",
    "iniciar_standalone.py",
    "iniciar_com_shell.ps1",
    "MPFM.bat",
    "mpfm_engine.py",
    "pytest.ini",
    "README.md",
    "README_EXECUCAO.txt",
    "recon_engine.py",
    "requirements.txt",
    "server.py",
    "start_app.ps1",
    "start_app_network.ps1",
    "startup.sh",
]

EXCLUDE_DIR_NAMES = {
    ".git",
    ".github",
    ".playwright-mcp",
    ".pytest_cache",
    ".venv",
    ".venv-1",
    ".vscode",
    "__pycache__",
    "node_modules",
    "dist",
    "release",
}

EXCLUDE_FILE_PATTERNS = [
    "*.pyc",
    "*.pyo",
    "*.tmp",
    "*.log",
    ".env",
    ".tmp_*",
    "*-lt-*.db",
    "*-lt-*.json",
    "*-lt-*.xlsx",
    "*.vsix",
    "dashboard-anp-radar*.zip",
    "materialcursompfm.zip",
]

PAINEL_KEEP_ROOT_FILES = {
    "MANIFESTO_ARQUIVOS_APLICACAO.md",
    "INSTRUCOES_TESTE.md",
    "start-radar-anp.bat",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    "index.html",
}

PAINEL_KEEP_DIRS = {
    "config",
    "data",
    "docs",
    "public",
    "scripts",
    "server",
    "src",
    "templates",
    "tests",
}


def _skip_path(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDE_DIR_NAMES:
        return True
    name = path.name
    return any(fnmatch.fnmatch(name, pattern) for pattern in EXCLUDE_FILE_PATTERNS)


def _copy_file(src: Path, dst: Path) -> int:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return 1


def _copy_tree(src: Path, dst: Path) -> int:
    if not src.exists():
        return 0
    count = 0
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        if _skip_path(rel) or _skip_path(path):
            if path.is_dir():
                continue
            continue
        if path.is_file():
            count += _copy_file(path, dst / rel)
    return count


def _snapshot_sqlite(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(src)
    try:
        target = sqlite3.connect(dst)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()


def _copy_data(stage: Path) -> int:
    data_src = ROOT / "data"
    data_dst = stage / "data"
    count = 0
    db = data_src / "mpfm_local.db"
    if db.exists():
        _snapshot_sqlite(db, data_dst / "mpfm_local.db")
        count += 1
    for name in ("cadastro.json", "state_2026_02.json", "state_2026_03.json", "state_2026_04.json", "state_2026_05.json", "state_2026_06.json"):
        src = data_src / name
        if src.exists():
            count += _copy_file(src, data_dst / name)
    prefs = data_src / "user_prefs.json"
    if prefs.exists():
        try:
            payload = json.loads(prefs.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        monitor = payload.get("auto_folder_monitor") or {}
        monitor["enabled"] = False
        monitor["folders"] = []
        payload["auto_folder_monitor"] = monitor
        payload.pop("__test_sentinel", None)
        (data_dst / "user_prefs.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        count += 1
    uploads = data_src / "uploads"
    if uploads.exists():
        count += _copy_tree(uploads, data_dst / "uploads")
    return count


def _copy_painel_operador(stage: Path) -> int:
    src = ROOT / "Painel_Operador" / "dashboard-anp-radar"
    if not src.exists():
        return 0
    dst = stage / "Painel_Operador" / "dashboard-anp-radar"
    count = 0
    for name in PAINEL_KEEP_ROOT_FILES:
        f = src / name
        if f.exists() and f.is_file() and not _skip_path(f):
            count += _copy_file(f, dst / name)
    for name in PAINEL_KEEP_DIRS:
        d = src / name
        if d.exists() and d.is_dir():
            count += _copy_tree(d, dst / name)
    return count


def _copy_twin(stage: Path) -> int:
    count = 0
    index = ROOT / "twin" / "index.html"
    if index.exists():
        count += _copy_file(index, stage / "twin" / "index.html")
    assets = ROOT / "twin" / "assets" / "a02"
    if assets.exists():
        count += _copy_tree(assets, stage / "twin" / "assets" / "a02")
    return count


def _write_release_notes(stage: Path, included: dict[str, int]) -> None:
    lines = [
        "# MPFM Manager - pacote de testes/producao",
        "",
        f"Gerado em: {dt.datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Como iniciar",
        "",
        "1. Instale Python 3.11+.",
        "2. Instale dependencias: `pip install -r requirements.txt`.",
        "3. Rode `python server.py` ou use `start_app.ps1`.",
        "4. Acesse `http://localhost:8765`.",
        "",
        "## Incluido",
        "",
    ]
    for key, value in included.items():
        lines.append(f"- {key}: {value} arquivo(s)")
    lines.extend(
        [
            "",
            "## Excluido de proposito",
            "",
            "- Ambientes virtuais, caches Python, logs temporarios e screenshots.",
            "- `data/backups`, bancos duplicados `*-lt-*`, `data/outputs` e pacotes antigos.",
            "- Builds portateis anteriores em `dist`.",
            "- Massa bruta pesada do Painel Operador, mantendo apenas o modulo `dashboard-anp-radar` sem `node_modules`, `MODELOS`, builds e zips.",
            "- Prototipos internos pesados do Twin, mantendo apenas `twin/index.html` e `twin/assets/a02` usados pela aplicacao.",
            "- `.env` e demais arquivos locais/sensiveis.",
        ]
    )
    (stage / "RELEASE_NOTES_LOCAL.md").write_text("\n".join(lines), encoding="utf-8")


def build_release() -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    stage = RELEASE_DIR / f"MPFM_NOVO_RELEASE_{stamp}"
    zip_path = RELEASE_DIR / f"MPFM_NOVO_RELEASE_{stamp}.zip"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True, exist_ok=True)

    included: dict[str, int] = {}
    root_count = 0
    for name in ROOT_FILES:
        src = ROOT / name
        if src.exists() and src.is_file():
            root_count += _copy_file(src, stage / name)
    included["arquivos raiz"] = root_count
    for name in SOURCE_DIRS:
        included[name] = _copy_tree(ROOT / name, stage / name)
    included["data minima"] = _copy_data(stage)
    included["Painel_Operador/dashboard-anp-radar"] = _copy_painel_operador(stage)
    included["twin runtime"] = _copy_twin(stage)
    _write_release_notes(stage, included)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in stage.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(stage))
    return zip_path


if __name__ == "__main__":
    release = build_release()
    print(release)
