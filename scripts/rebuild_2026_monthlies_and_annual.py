from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server
from services.importing.monthly_workbook_service import BASE_UNICA_COLUMNS


def main() -> int:
    root = ROOT
    db_path = root / "data" / "mpfm_local.db"
    out_dir = root / "data" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    months = [
        r[0]
        for r in cur.execute(
            """
            SELECT DISTINCT substr(day_ref,1,7) AS month_key
            FROM measurements_curated
            WHERE day_ref LIKE '2026-%'
              AND row_kind IN ('hourly','daily','recon','sep')
            ORDER BY month_key
            """
        ).fetchall()
    ]

    print("DB:", db_path)
    print("Months:", ", ".join(months) if months else "none")

    for month_key in months:
        yr, mo = month_key.split("-")
        workbook_path = server.OUTPUT_DIR / server.excel_name(yr, mo)
        print(f"[MONTHLY] rebuilding {workbook_path.name}")
        server.build_monthly_base_unica(workbook_path, yr, mo)
        server._cleanup_workbook(workbook_path)

    rows = cur.execute(
        """
        SELECT day_ref, hour_ref, row_kind, bank, loop, tipo, tag, instrument, metric_name, metric_value, source_file
        FROM measurements_curated
        WHERE day_ref LIKE '2026-%'
          AND row_kind IN ('hourly','daily','recon','sep')
        ORDER BY day_ref, COALESCE(hour_ref,-1), row_kind, bank, tag, metric_name
        """
    ).fetchall()
    conn.close()

    piv = defaultdict(dict)
    meta = {}
    for row in rows:
        key = (
            row["day_ref"],
            row["hour_ref"],
            row["row_kind"],
            row["bank"],
            row["loop"],
            row["tipo"],
            row["tag"],
            row["instrument"],
            row["source_file"],
        )
        piv[key][row["metric_name"]] = row["metric_value"]
        meta[key] = {
            "ProductionDate": row["day_ref"],
            "Hour": "" if row["hour_ref"] is None else f"{int(row['hour_ref']):02d}:00",
            "Granularity": (
                "Hourly"
                if row["row_kind"] == "hourly"
                else "Daily"
                if row["row_kind"] == "daily"
                else "Recon"
                if row["row_kind"] == "recon"
                else ("Hourly" if row["hour_ref"] is not None else "Daily")
            ),
            "Origin": "SEP" if row["row_kind"] == "sep" else ("RECON" if row["row_kind"] == "recon" else "MPFM"),
            "SourceType": "TXT" if row["row_kind"] == "sep" else ("CALC" if row["row_kind"] == "recon" else "PDF"),
            "Area": "",
            "System": "",
            "Bank": "" if row["bank"] == "SEP" else (row["bank"] or ""),
            "Loop": row["loop"] or "",
            "Tipo": row["tipo"] or "",
            "Entity": row["tag"] or "",
            "Tag": row["tag"] or "",
            "Instrumento": row["instrument"] or "",
            "Fonte": "Separador" if row["row_kind"] == "sep" else ("Reconciliation" if row["row_kind"] == "recon" else "MPFM"),
            "SourceFile": row["source_file"] or "",
            "IsOfficial": 1,
        }

    out_rows = []
    for key in sorted(
        piv.keys(),
        key=lambda item: (item[0], -1 if item[1] is None else item[1], item[2], item[3], item[6]),
    ):
        out_row = {column: "" for column in BASE_UNICA_COLUMNS}
        out_row.update(meta[key])
        values = piv[key]

        for column in BASE_UNICA_COLUMNS:
            if column in values:
                out_row[column] = values[column]

        if meta[key]["Origin"] == "SEP":
            out_row["SEP TAG"] = meta[key]["Tag"] or "SEP"
            out_row["SEP Medidor"] = meta[key]["Instrumento"]
            out_row["SEP Local"] = meta[key]["Loop"] or meta[key]["Tipo"]
            out_row["SEP Status"] = "Extracted"
            metric_map = {
                "oil_m3": "SEP Oleo Vol. Bruto (m3) CV",
                "oil_t": "SEP Oleo (t) CV",
                "gas_t": "SEP Gas (t) CV",
                "water_t": "SEP Agua (t) CV",
                "hc_t": "SEP HC (t)",
                "total_t": "SEP Total (t)",
                "temp": "SEP Temperatura Med. (C)",
                "pressure_barg": "SEP Pressao Med. (barg)",
            }
            for metric, column in metric_map.items():
                if metric in values and column in out_row:
                    out_row[column] = values[metric]

        if meta[key]["Origin"] == "RECON":
            recon_map = {
                "Cobertura": "Recon Cobertura",
                "Horas": "Recon Horas",
                "Daily Gas (t)": "Recon Daily Gas (t)",
                "Daily Oleo (t)": "Recon Daily Oleo (t)",
                "Daily HC (t)": "Recon Daily HC (t)",
                "Daily Agua (t)": "Recon Daily Agua (t)",
                "Soma h. Gas (t)": "Recon Soma h. Gas (t)",
                "Soma h. Oleo (t)": "Recon Soma h. Oleo (t)",
                "Soma h. HC (t)": "Recon Soma h. HC (t)",
                "Soma h. Agua (t)": "Recon Soma h. Agua (t)",
                "Delta Gas (t)": "Recon Delta Gas (t)",
                "Delta Oleo (t)": "Recon Delta Oleo (t)",
                "Delta HC (t)": "Recon Delta HC (t)",
                "Delta Agua (t)": "Recon Delta Agua (t)",
                "Status Gas": "Status Gas",
                "Status Oleo": "Status Oleo",
                "Status HC": "Status HC",
                "Status Agua": "Status Agua",
            }
            for metric, column in recon_map.items():
                if metric in values and column in out_row:
                    out_row[column] = values[metric]

        out_rows.append(out_row)

    full_df = pd.DataFrame(out_rows, columns=BASE_UNICA_COLUMNS)
    annual_path = out_dir / "MPFM_2026_BASE_UNICA_CONSOLIDADO.xlsx"

    with pd.ExcelWriter(annual_path, engine="openpyxl") as writer:
        full_df.to_excel(writer, sheet_name="BASE_UNICA_2026", index=False)
        full_df[(full_df["Granularity"] == "Daily") & (full_df["Origin"] != "RECON")].to_excel(
            writer, sheet_name="DAILYS_2026", index=False
        )
        full_df[(full_df["Granularity"] == "Hourly") & (full_df["Origin"] != "RECON")].to_excel(
            writer, sheet_name="HOURLYS_2026", index=False
        )
        full_df[(full_df["Origin"] == "RECON")].to_excel(writer, sheet_name="RECON_2026", index=False)
        full_df[(full_df["Origin"] == "SEP")].to_excel(writer, sheet_name="SEP_2026", index=False)

    print(f"[ANNUAL] created {annual_path}")
    print(f"[ANNUAL] rows={len(full_df)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
