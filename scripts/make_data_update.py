"""
make_data_update.py
===================
Gera um pacote ZIP apenas com os DADOS para atualizar uma instalação
existente da aplicação MPFM (mesma versão de código, dados desatualizados).

O que inclui:
  - data/mpfm_local.db          (banco completo e atualizado)
  - data/outputs/MPFM_*.xlsx    (workbooks mensais limpos)
  - data/cadastro.json          (configuração de poços)
  - APLICAR_ATUALIZACAO.ps1     (script PowerShell de aplicação)
  - APLICAR_ATUALIZACAO.bat     (lançador rápido do script)
  - COMO_APLICAR.txt            (instruções)

O que NÃO inclui:
  - Código da aplicação (routes/, services/, static/, etc.)
  - Workbooks temporários (*-lt-*.xlsx)
  - Backups ZIP
  - data/uploads/ (temporários de upload)
  - user_prefs.json (cada instalação mantém suas próprias preferências)

Uso:
  python scripts/make_data_update.py

Saida: ../MPFM_DATA_<data>.zip  (pasta pai da aplicacao)
"""

import os
import zipfile
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DB       = os.path.join(ROOT, "data", "mpfm_local.db")
DATA_CADASTRO = os.path.join(ROOT, "data", "cadastro.json")
OUTPUTS_DIR   = os.path.join(ROOT, "data", "outputs")


def _is_main_workbook(name: str) -> bool:
    if name.endswith(".zip"):
        return False
    if "-lt-" in name:
        return False
    return name.endswith(".xlsx")


def _make_ps1() -> str:
    return r"""# APLICAR_ATUALIZACAO.ps1
# Aplica o pacote de dados MPFM em uma instalação existente.
#
# Uso:
#   .\APLICAR_ATUALIZACAO.ps1                        # modo interativo
#   .\APLICAR_ATUALIZACAO.ps1 -AppPath "C:\MPFM_APP" # modo silencioso

param(
    [string]$AppPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  MPFM Manager — Aplicar Atualização de Dados" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── Descobrir caminho da aplicação ─────────────────────────────────────────
if (-not $AppPath) {
    $AppPath = Read-Host "Informe o caminho da pasta onde a aplicação MPFM está instalada"
}

$AppPath = $AppPath.Trim('"').Trim("'")

if (-not (Test-Path $AppPath)) {
    Write-Host "ERRO: Pasta não encontrada: $AppPath" -ForegroundColor Red
    Read-Host "Pressione Enter para fechar"
    exit 1
}

$serverCheck = Join-Path $AppPath "server.py"
if (-not (Test-Path $serverCheck)) {
    Write-Host "AVISO: server.py não encontrado em '$AppPath'." -ForegroundColor Yellow
    Write-Host "Verifique se o caminho informado é o correto." -ForegroundColor Yellow
    $confirm = Read-Host "Continuar mesmo assim? (s/N)"
    if ($confirm -notmatch "^[sS]") { exit 1 }
}

Write-Host "Aplicando em: $AppPath" -ForegroundColor White
Write-Host ""

# ── Parar servidor se estiver rodando ──────────────────────────────────────
Write-Host "[1/4] Verificando servidor..."
try {
    $conn = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $pid_ = $conn.OwningProcess | Select-Object -First 1
        Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue
        Write-Host "      Servidor parado (PID $pid_)." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    } else {
        Write-Host "      Servidor não estava rodando." -ForegroundColor Gray
    }
} catch {
    Write-Host "      Não foi possível verificar o servidor (continuando)." -ForegroundColor Gray
}

# ── Garantir pasta data/outputs ────────────────────────────────────────────
$outDir = Join-Path $AppPath "data\outputs"
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir | Out-Null
}

# ── Copiar banco de dados ──────────────────────────────────────────────────
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$dbSrc  = Join-Path $scriptDir "data\mpfm_local.db"
$dbDest = Join-Path $AppPath   "data\mpfm_local.db"

if (Test-Path $dbSrc) {
    Write-Host "[2/4] Copiando banco de dados..."
    $sizeMB = [math]::Round((Get-Item $dbSrc).Length / 1MB, 1)
    Write-Host "      mpfm_local.db ($sizeMB MB) — pode demorar alguns segundos..."
    Copy-Item $dbSrc -Destination $dbDest -Force
    Write-Host "      OK." -ForegroundColor Green
} else {
    Write-Host "[2/4] AVISO: mpfm_local.db não encontrado neste pacote." -ForegroundColor Yellow
}

# ── Copiar cadastro.json ───────────────────────────────────────────────────
$cadSrc  = Join-Path $scriptDir "data\cadastro.json"
$cadDest = Join-Path $AppPath   "data\cadastro.json"
if (Test-Path $cadSrc) {
    Write-Host "[3/4] Copiando cadastro.json..."
    Copy-Item $cadSrc -Destination $cadDest -Force
    Write-Host "      OK." -ForegroundColor Green
}

# ── Copiar workbooks Excel ─────────────────────────────────────────────────
Write-Host "[4/4] Copiando workbooks Excel..."
$xlsSrc = Join-Path $scriptDir "data\outputs"
if (Test-Path $xlsSrc) {
    $files = Get-ChildItem $xlsSrc -Filter "*.xlsx"
    foreach ($f in $files) {
        Copy-Item $f.FullName -Destination $outDir -Force
        Write-Host "      + $($f.Name)" -ForegroundColor Gray
    }
    Write-Host "      $($files.Count) arquivo(s) copiado(s)." -ForegroundColor Green
} else {
    Write-Host "      AVISO: pasta data\outputs não encontrada neste pacote." -ForegroundColor Yellow
}

# ── Conclusão ──────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Atualização aplicada com sucesso!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Reinicie a aplicação normalmente (iniciar_simples.bat ou python server.py)."
Write-Host ""
Read-Host "Pressione Enter para fechar"
"""


def _make_bat() -> str:
    return r"""@echo off
:: Lançador do script de atualização de dados MPFM
:: Duplo clique para executar

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0APLICAR_ATUALIZACAO.ps1"
"""


def _make_readme() -> str:
    return (
        "========================================\n"
        "  MPFM Manager -- Pacote de Atualizacao de Dados\n"
        "========================================\n"
        "\n"
        "USE ESTE PACOTE SE:\n"
        "  Voce ja tem a aplicacao MPFM instalada e funcionando,\n"
        "  mas deseja atualizar os dados (banco + workbooks) para\n"
        "  a versao mais recente.\n"
        "\n"
        "  NAO e necessario reinstalar a aplicacao.\n"
        "\n"
        "O QUE ESTE PACOTE CONTEM:\n"
        "  - data/mpfm_local.db   -> banco de dados atualizado\n"
        "  - data/outputs/*.xlsx  -> workbooks mensais (Out/25 -> Abr/26)\n"
        "  - data/cadastro.json   -> configuracao dos pocos\n"
        "  - APLICAR_ATUALIZACAO.ps1 / .bat -> script de aplicacao automatica\n"
        "\n"
        "COMO APLICAR (opcao rapida -- Windows):\n"
        "  1. Extraia o conteudo desta pasta para um local temporario.\n"
        r"     Exemplo: C:\Temp\MPFM_DATA" + "\n"
        "\n"
        "  2. Execute APLICAR_ATUALIZACAO.bat com duplo clique.\n"
        "\n"
        "  3. Quando solicitado, informe o caminho completo da pasta\n"
        "     onde a aplicacao MPFM esta instalada.\n"
        r"     Exemplo: C:\Users\SEU_USUARIO\MPFM_APP" + "\n"
        "\n"
        "  4. O script ira:\n"
        "       - Parar o servidor (se estiver rodando na porta 8765)\n"
        "       - Substituir o banco de dados\n"
        "       - Copiar os workbooks Excel\n"
        "       - Confirmar o sucesso\n"
        "\n"
        "  5. Reinicie a aplicacao normalmente.\n"
        "\n"
        "COMO APLICAR (opcao manual):\n"
        "  1. Pare o servidor (feche o terminal onde esta rodando).\n"
        "  2. Copie data/mpfm_local.db  ->  <pasta da app>/data/mpfm_local.db\n"
        "  3. Copie data/outputs/*.xlsx ->  <pasta da app>/data/outputs/\n"
        "  4. Copie data/cadastro.json  ->  <pasta da app>/data/cadastro.json\n"
        "  5. Reinicie o servidor.\n"
        "\n"
        "NOTA SOBRE PREFERENCIAS:\n"
        "  As preferencias do usuario (user_prefs.json) NAO sao\n"
        "  alteradas por este pacote. Suas configuracoes de pastas\n"
        "  monitoradas, tema e outros ajustes permanecem intactos.\n"
        "\n"
        "========================================\n"
    )


def build_data_package() -> str:
    date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    dist_name = f"MPFM_DATA_{date_str}.zip"
    dist_path = os.path.join(os.path.dirname(ROOT), dist_name)

    print(f"\n{'═'*60}")
    print(f"  Gerando pacote de ATUALIZAÇÃO DE DADOS MPFM")
    print(f"  Destino: {dist_path}")
    print(f"{'═'*60}\n")

    total_files = 0
    total_bytes = 0

    with zipfile.ZipFile(dist_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:

        # ── Banco de dados ────────────────────────────────────────────────
        print("[ 1/4 ] Banco de dados...")
        if os.path.exists(DATA_DB):
            sz = os.path.getsize(DATA_DB) / 1024 / 1024
            print(f"    + data/mpfm_local.db  ({sz:.1f} MB) — comprimindo...")
            zf.write(DATA_DB, arcname="data/mpfm_local.db")
            total_files += 1
            total_bytes += os.path.getsize(DATA_DB)
        else:
            print("    ⚠  mpfm_local.db não encontrado!")

        # ── cadastro.json ─────────────────────────────────────────────────
        if os.path.exists(DATA_CADASTRO):
            zf.write(DATA_CADASTRO, arcname="data/cadastro.json")
            total_files += 1
            total_bytes += os.path.getsize(DATA_CADASTRO)
            print("    + data/cadastro.json")

        # ── Workbooks Excel ───────────────────────────────────────────────
        print(f"\n[ 2/4 ] Workbooks Excel...")
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
            print(f"    {wb_count} workbook(s)")

        # ── Scripts de aplicação ──────────────────────────────────────────
        print(f"\n[ 3/4 ] Scripts de aplicação...")
        zf.writestr("APLICAR_ATUALIZACAO.ps1", _make_ps1().encode("utf-8"))
        zf.writestr("APLICAR_ATUALIZACAO.bat", _make_bat().encode("utf-8"))
        print("    + APLICAR_ATUALIZACAO.ps1")
        print("    + APLICAR_ATUALIZACAO.bat")

        # ── Instruções ────────────────────────────────────────────────────
        print(f"\n[ 4/4 ] Instruções...")
        zf.writestr("COMO_APLICAR.txt", _make_readme().encode("utf-8"))
        print("    + COMO_APLICAR.txt")

    zip_size = os.path.getsize(dist_path) / 1024 / 1024
    print(f"\n{'═'*60}")
    print(f"  ✓  Pacote de dados gerado!")
    print(f"  Arquivos incluídos: {total_files:,}")
    print(f"  Dados originais:    {total_bytes/1024/1024:.1f} MB")
    print(f"  Tamanho do ZIP:     {zip_size:.1f} MB")
    print(f"  Arquivo:            {dist_path}")
    print(f"{'═'*60}\n")
    return dist_path


if __name__ == "__main__":
    build_data_package()
