#!/usr/bin/env python3
"""
Carrega PDFs MPFM Daily e Hourly de abril/2026 (dias 13-17 e 20-27)
para a API local em lotes, reduzindo transações e reconstruções de Excel.

Padrão de nome: B03_MPFM_Daily-20260413-000000+0000.pdf
                B03_MPFM_Hourly-20260413-010000+0000.pdf

Exclui automaticamente alarmes, RANP44, Topside Gas Injection B18 e Zip.
"""

import re, pathlib, requests, sys, io
from contextlib import ExitStack
from base64 import b64encode

# Força stdout UTF-8 para evitar erros de encoding no Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_REPORTS = pathlib.Path(
    r"C:\Users\MAUAM\OneDrive - Equinor\Desktop\DPB FPSO Bacalhau - Metering - 3.2 Daily Reports"
)
API_URL = "http://localhost:8765/api/process-files"
AUTH    = b64encode(b"mpfm:mpfm2024").decode()
HEADERS = {"Authorization": f"Basic {AUTH}"}

# Dias alvo: 13-17 e 20-27 de abril 2026 (formato YYYYMMDD usado no nome do arquivo)
TARGET_YYYYMMDD = set(
    [f"202604{d:02d}" for d in range(13, 18)] +
    [f"202604{d:02d}" for d in range(20, 28)]
)

# Regex para extrair YYYYMMDD do nome: ex. B03_MPFM_Daily-20260413-000000+0000.pdf
RE_DATE = re.compile(r"[-_](\d{8})-")

SKIP_DIRS = {"ALARMES", "ZIP", "RANP44", "TOPSIDE GAS INJECTION B18"}

def skip_dir(name: str) -> bool:
    n = name.upper()
    return any(s in n for s in SKIP_DIRS)

def collect_pdfs(tipo: str) -> list[pathlib.Path]:
    """Coleta PDFs do tipo 'daily' ou 'hourly' para os dias alvo, ordenados por pasta e data."""
    tipo_str = tipo.lower()   # 'daily' or 'hourly'
    found = []
    for subdir in sorted(BASE_REPORTS.iterdir()):
        if not subdir.is_dir() or skip_dir(subdir.name):
            print(f"  [SKIP] {subdir.name}")
            continue
        for pdf in sorted(subdir.rglob("*.pdf")):
            nome = pdf.name.lower()
            if tipo_str not in nome:
                continue
            m = RE_DATE.search(pdf.name)
            if m and m.group(1) in TARGET_YYYYMMDD:
                found.append(pdf)
    return found

def upload_batch(pdf_paths: list[pathlib.Path], idx: int, total: int) -> dict:
    """Envia um lote em uma única execução transacional da API."""
    first = pdf_paths[0].name
    last = pdf_paths[-1].name
    print(f"[{idx:04d}/{total}] lote={len(pdf_paths)} | {first} ... {last}", flush=True)
    try:
        with ExitStack() as stack:
            files = [
                ("files", (path.name, stack.enter_context(path.open("rb")), "application/pdf"))
                for path in pdf_paths
            ]
            resp = requests.post(
                API_URL,
                headers=HEADERS,
                files=files,
                timeout=1800,
            )
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "?") if isinstance(data, dict) else "ok"
            print(f"  -> OK ({status})", flush=True)
            return {"status": "ok", "files": [p.name for p in pdf_paths], "result": data}
        else:
            print(f"  -> ERRO HTTP {resp.status_code}: {resp.text[:150]}", flush=True)
            return {"status": "error", "files": [p.name for p in pdf_paths], "http": resp.status_code}
    except Exception as e:
        print(f"  -> EXCECAO: {e}", flush=True)
        return {"status": "exception", "files": [p.name for p in pdf_paths], "error": str(e)}

def run_phase(tipo: str, batch_size: int) -> tuple[int, int]:
    label = tipo.upper()
    print(f"\n{'-'*70}")
    print(f"FASE - PDFs {label}")
    print("-"*70)
    pdfs = collect_pdfs(tipo)
    print(f"\n  {len(pdfs)} arquivos {label} encontrados para os dias alvo\n")
    if not pdfs:
        print(f"  Nenhum PDF {label} encontrado — verifique padrão de nome.")
        return 0, 0
    batches = [pdfs[i:i + batch_size] for i in range(0, len(pdfs), batch_size)]
    results = [upload_batch(batch, i, len(batches)) for i, batch in enumerate(batches, 1)]
    ok = sum(len(r["files"]) for r in results if r["status"] == "ok")
    erros = [r for r in results if r["status"] != "ok"]
    print(f"\n  {label} concluído: {ok}/{len(pdfs)} OK")
    if erros:
        print(f"  Erros ({len(erros)}):")
        for e in erros:
            print(f"    {len(e['files'])} arquivos ({e['files'][0]}...) -> {e.get('http', e.get('error', '?'))}")
    return ok, len(pdfs)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Carrega PDFs MPFM abril/2026")
    parser.add_argument("--phase", choices=["daily", "hourly", "all"], default="all",
                        help="Fase a executar: daily, hourly ou all (padrao: all)")
    parser.add_argument("--batch-size", type=int, default=100,
                        help="Quantidade de PDFs por requisição (padrão: 100)")
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size deve ser maior que zero")

    print("="*70)
    print("MPFM Load - April 2026 Daily + Hourly (dias 13-17 e 20-27)")
    print("="*70)
    print(f"Pasta base : {BASE_REPORTS}")
    print(f"Dias alvo  : {sorted(TARGET_YYYYMMDD)}")
    print(f"Fase       : {args.phase.upper()}")

    ok_d = tot_d = 0
    ok_h = tot_h = 0

    if args.phase in ("daily", "all"):
        ok_d, tot_d = run_phase("daily", args.batch_size)

    if args.phase in ("hourly", "all"):
        ok_h, tot_h = run_phase("hourly", args.batch_size)

    print(f"\n{'='*70}")
    print("RESUMO FINAL")
    print("="*70)
    if args.phase in ("daily", "all"):
        print(f"  Daily : {ok_d}/{tot_d} OK")
    if args.phase in ("hourly", "all"):
        print(f"  Hourly: {ok_h}/{tot_h} OK")
    total_ok = ok_d + ok_h
    total    = tot_d + tot_h
    print(f"  TOTAL : {total_ok}/{total} OK")
    if total_ok == total and total > 0:
        print("\n  Todos os arquivos carregados com sucesso!")

if __name__ == "__main__":
    main()
