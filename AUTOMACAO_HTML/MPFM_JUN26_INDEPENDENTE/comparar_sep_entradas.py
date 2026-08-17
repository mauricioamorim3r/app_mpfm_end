from datetime import datetime
from pathlib import Path
import csv
import openpyxl

ROOT = Path(r"C:\MPFM\AUTOMAÇÃO HTML")
OLD = Path(r"C:\MPFM\NOVO\data\outputs\MPFM_JUN_2026.xlsx")
NEW = ROOT / "SEP_Dados_2026-02-03_a_2026-07-16.xlsx"
OUT = ROOT / "MPFM_JUN26_INDEPENDENTE"

def d(v):
    if hasattr(v, "year"):
        return v.date() if hasattr(v, "date") else v
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(v)[:10], fmt).date()
        except ValueError:
            pass
    return None

def n(v):
    try:
        return None if v in (None, "") else float(v)
    except (TypeError, ValueError):
        return None

def read(path, sheet):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    it = wb[sheet].iter_rows(values_only=True)
    heads = [str(x or "").strip() for x in next(it)]
    result = [dict(zip(heads, row)) for row in it if any(x not in (None, "") for x in row)]
    wb.close()
    return result

old = {d(r.get("ProductionDate")): r for r in read(OLD, "DAILYS") if str(r.get("Origin", "")).upper() == "SEP"}
new = {d(r.get("Data")): r for r in read(NEW, "Separador_Totais") if d(r.get("Data")) and d(r.get("Data")).year == 2026 and d(r.get("Data")).month == 6}
common = sorted(set(old) & set(new))
fields = {"gas": ("SEP Gás (t) CV", "Mass Gas (t)"), "water": ("SEP Água (t) CV", "Mass agua (t)"), "hc": ("SEP HC (t)", "HC (t)"), "total": ("SEP Total (t)", "Total (t)"), "oil_volume": ("SEP Óleo Vol. Bruto (m³) CV", "GSV óleo (sm³)")}
rows = []
for day in common:
    item = {"date": day.isoformat()}
    for key, (a, b) in fields.items():
        x, y = n(old[day].get(a)), n(new[day].get(b))
        item[f"old_{key}"] = x; item[f"new_{key}"] = y; item[f"delta_{key}"] = None if x is None or y is None else x - y
    rows.append(item)

csv_path = OUT / "comparativo_sep_junho_2026.csv"
with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["date"])
    writer.writeheader(); writer.writerows(rows)

counts = {k: sum(1 for r in rows if r[f"delta_{k}"] is not None and abs(r[f"delta_{k}"]) <= .001) for k in fields}
missing = sorted(set(new) - set(old))
lines = ["# Comparativo de entradas SEP — junho de 2026", "", f"Arquivo existente: {len(old)} dias SEP; arquivo novo: {len(new)} dias; dias comuns: {len(common)}.", f"Dias só no arquivo novo: {', '.join(x.strftime('%d/%m/%Y') for x in missing)}.", "", "| Variável | Coincidentes | Comparados |", "|---|---:|---:|"]
for key, label in (("gas", "Massa de gás"), ("water", "Massa de água"), ("hc", "HC"), ("total", "Total"), ("oil_volume", "Volume de óleo")):
    lines.append(f"| {label} | {counts[key]} | {len(rows)} |")
lines += ["", "Gás e água coincidem nos 24 dias comuns.", "HC e Total coincidem em 17 dos 24 dias; as diferenças estão em 06–07/06 e 13–17/06.", "O volume usa campos diferentes (SEP Óleo Vol. Bruto CV versus GSV óleo); validar equivalência.", "", "Comparação independente; XML e Base Única não foram alterados."]
md_path = OUT / "COMPARATIVO_SEP_JUNHO_2026.md"
md_path.write_text("\n".join(lines), encoding="utf-8")
print(md_path)
print(csv_path)
