"""
Exporta dados brutos (MPFM subsea/topside + Separador) para Excel.

Escopo:
  - Periodo: 2026-02-01 a 2026-07-31 (ontem, considerando "hoje" = 2026-08-01)
  - Pontos MPFM: PE-04, PE-02, PW-104DA (subsea) e Riser P2, Riser P4, Riser P5 (topside)
  - Todas as variaveis (metric_name) ja existentes em measurements_curated para
    row_kind = daily, hourly e recon
  - Dados do Separador (bank='SEP'): consolidado (row_kind='sep') e detalhes
    horarios de oleo/gas/agua (sep_oleo_detail, sep_gas_detail, sep_agua_detail)

Saida: data/outputs/Export_MPFM_SEP_2026-02-01_a_2026-07-31_<timestamp>.xlsx
"""
import sqlite3
import sys
from datetime import datetime

import pandas as pd

DB_PATH = "data/mpfm_local.db"
DATE_FROM = "2026-02-01"
DATE_TO = "2026-07-31"

MPFM_POINTS = [
    ("B05", "PE_4", "PE-04 (Subsea)"),
    ("B10", "PE_2", "PE-02 (Subsea)"),
    ("B15", "PW-104DA", "PW-104DA (Subsea)"),
    ("B08", "Riser_P2", "Riser P2 (Topside)"),
    ("B13", "Riser_P4", "Riser P4 (Topside)"),
    ("B03", "Riser_P5", "Riser P5 (Topside)"),
]

SEP_TAG_LABELS = {
    "20FT0247": "Oleo (20FT0247)",
    "20FT0244": "Gas (20FT0244)",
    "20FT0251": "Agua (20FT0251)",
    "SEP": "Consolidado 24h (SEP)",
}


def load_rows(conn, row_kind, bank_tag_pairs=None, bank=None):
    q = """
        SELECT bank, tag, day_ref, hour_ref, metric_name, metric_value, metric_unit
        FROM measurements_curated
        WHERE row_kind = ?
          AND day_ref BETWEEN ? AND ?
    """
    params = [row_kind, DATE_FROM, DATE_TO]
    if bank_tag_pairs:
        placeholders = ",".join(["(?,?)"] * len(bank_tag_pairs))
        q += f" AND (bank,tag) IN ({placeholders})"
        for b, t in bank_tag_pairs:
            params.extend([b, t])
    if bank:
        q += " AND bank = ?"
        params.append(bank)
    return pd.read_sql_query(q, conn, params=params)


def pivot_wide(df, index_cols, label_map=None, label_col_name="Ponto", label_by_bank_tag=False):
    if df.empty:
        return pd.DataFrame(columns=index_cols)
    wide = df.pivot_table(
        index=index_cols, columns="metric_name", values="metric_value", aggfunc="first"
    )
    wide = wide.reset_index()
    wide.columns.name = None
    if label_map is not None:
        if label_by_bank_tag:
            keys = list(zip(wide["bank"], wide["tag"]))
            wide.insert(0, label_col_name, [label_map.get(k, f"{k[0]}/{k[1]}") for k in keys])
        else:
            wide.insert(0, label_col_name, wide["tag"].map(label_map).fillna(wide["tag"]))
    sort_cols = [c for c in ("day_ref", "hour_ref") if c in wide.columns]
    if sort_cols:
        extra = [c for c in ("bank", "tag") if c in wide.columns]
        wide = wide.sort_values(by=extra + sort_cols if extra else sort_cols).reset_index(drop=True)
    rename = {"day_ref": "Data", "hour_ref": "Hora", "bank": "Bank", "tag": "Tag"}
    wide = wide.rename(columns=rename)
    return wide


def main():
    conn = sqlite3.connect(DB_PATH)
    label_map_mpfm = {(b, t): lbl for b, t, lbl in MPFM_POINTS}
    bank_tag_pairs = [(b, t) for b, t, _ in MPFM_POINTS]

    print("Lendo MPFM diario...")
    df_daily = load_rows(conn, "daily", bank_tag_pairs=bank_tag_pairs)
    sheet_daily = pivot_wide(df_daily, ["bank", "tag", "day_ref"], label_map_mpfm, label_by_bank_tag=True)

    print("Lendo MPFM horario...")
    df_hourly = load_rows(conn, "hourly", bank_tag_pairs=bank_tag_pairs)
    sheet_hourly = pivot_wide(df_hourly, ["bank", "tag", "day_ref", "hour_ref"], label_map_mpfm, label_by_bank_tag=True)

    print("Lendo MPFM reconciliacao...")
    df_recon = load_rows(conn, "recon", bank_tag_pairs=bank_tag_pairs)
    sheet_recon = pivot_wide(df_recon, ["bank", "tag", "day_ref"], label_map_mpfm, label_by_bank_tag=True)

    print("Lendo Separador consolidado...")
    df_sep = load_rows(conn, "sep", bank="SEP")
    sheet_sep = pivot_wide(df_sep, ["tag", "day_ref", "hour_ref"], SEP_TAG_LABELS)

    print("Lendo Separador detalhe oleo...")
    df_sep_oleo = load_rows(conn, "sep_oleo_detail", bank="SEP")
    sheet_sep_oleo = pivot_wide(df_sep_oleo, ["tag", "day_ref", "hour_ref"], SEP_TAG_LABELS)

    print("Lendo Separador detalhe gas...")
    df_sep_gas = load_rows(conn, "sep_gas_detail", bank="SEP")
    sheet_sep_gas = pivot_wide(df_sep_gas, ["tag", "day_ref", "hour_ref"], SEP_TAG_LABELS)

    print("Lendo Separador detalhe agua...")
    df_sep_agua = load_rows(conn, "sep_agua_detail", bank="SEP")
    sheet_sep_agua = pivot_wide(df_sep_agua, ["tag", "day_ref", "hour_ref"], SEP_TAG_LABELS)

    conn.close()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"data/outputs/Export_MPFM_SEP_2026-02-01_a_2026-07-31_{ts}.xlsx"

    sheets = [
        ("MPFM_Diario", sheet_daily),
        ("MPFM_Horario", sheet_hourly),
        ("MPFM_Reconciliacao", sheet_recon),
        ("SEP_Consolidado", sheet_sep),
        ("SEP_Detalhe_Oleo", sheet_sep_oleo),
        ("SEP_Detalhe_Gas", sheet_sep_gas),
        ("SEP_Detalhe_Agua", sheet_sep_agua),
    ]

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for name, df in sheets:
            df.to_excel(writer, sheet_name=name[:31], index=False)

    print()
    print("=== RESUMO ===")
    for name, df in sheets:
        print(f"{name}: {len(df)} linhas, {len(df.columns)} colunas")
    print(f"Arquivo gerado: {out_path}")


if __name__ == "__main__":
    sys.exit(main())
