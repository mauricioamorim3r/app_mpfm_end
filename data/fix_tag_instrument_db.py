"""
Corrige entradas em measurements_curated onde tag = instrument (código FT)
em vez do nome operacional (Riser_P5, PE_4, etc).

Modo padrão (sem flags): mostra diagnóstico e quantidades afetadas.
  --apply-update   : atualiza o campo tag para o nome operacional correto.
  --delete-dupes   : após o update, exclui linhas que ficaram duplicadas
                     (mesma combinação run_id≠principal, day_ref, hour_ref,
                     instrument, metric_name — mantém a linha com run_id mais
                     recente ou com tag já correto antes do fix).

Exemplo de uso:
  python data/fix_tag_instrument_db.py
  python data/fix_tag_instrument_db.py --apply-update
  python data/fix_tag_instrument_db.py --apply-update --delete-dupes
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "mpfm_local.db"

INSTRUMENT_ENTITY = {
    "13FT0367": "Riser_P5",
    "13FT0417": "Riser_P6",
    "18FT1506": "PE_4",
    "18FT1706": "PE_EO105",
    "18FT1406": "PE_EO10",
    "18FT1806": "PE_EO4",
    "13FT0167": "Riser_P1",
    "13FT0217": "Riser_P2",
    "18FT0506": "PE_2",
    "18FT0306": "PE_8",
    "18FT0106": "PE_9",
    "13FT0267": "Riser_P3",
    "13FT0317": "Riser_P4",
    "18FT0706": "PE_1",
    "18FT0906": "PI_1",
    "18FT1206": "PI_2",
    "18FT1106": "PW-104DA",
}


def main():
    parser = argparse.ArgumentParser(description="Corrige tag=instrument no banco SQLite.")
    parser.add_argument("--apply-update", action="store_true", help="Aplica o UPDATE no banco.")
    parser.add_argument("--delete-dupes", action="store_true", help="Remove duplicatas após o update.")
    parser.add_argument("--db", default=str(DB_PATH), help="Caminho para mpfm_local.db.")
    args = parser.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"ERRO: banco não encontrado: {db}")
        return 1

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # ── Diagnóstico ──────────────────────────────────────────────────────────
    print("=" * 60)
    print("DIAGNÓSTICO: linhas com tag = instrument (código FT)")
    print("=" * 60)
    total_wrong = 0
    for instrument, entity in INSTRUMENT_ENTITY.items():
        cur.execute(
            "SELECT COUNT(*) FROM measurements_curated WHERE instrument = ? AND tag = ?",
            (instrument, instrument),
        )
        count = cur.fetchone()[0]
        if count:
            print(f"  {instrument:12s}  ->  {entity:12s}  :  {count:>7,} linhas erradas")
            total_wrong += count

    print(f"\nTotal de linhas com tag = instrument: {total_wrong:,}")

    if total_wrong == 0:
        print("Nenhuma linha com tag errado. Banco já está correto (update não necessário).")
        if not args.delete_dupes:
            conn.close()
            return 0
        # Pula para a verificação de duplicatas mesmo sem update
    elif not args.apply_update:
        print("\nPara aplicar a correção, execute novamente com --apply-update")
        conn.close()
        return 0

    # ── Update ────────────────────────────────────────────────────────────────
    if total_wrong > 0:
        print("\nAplicando UPDATE...")
        updated_total = 0
        for instrument, entity in INSTRUMENT_ENTITY.items():
            cur.execute(
                "UPDATE measurements_curated SET tag = ? WHERE instrument = ? AND tag = ?",
                (entity, instrument, instrument),
            )
            n = cur.rowcount
            if n:
                print(f"  {instrument} -> {entity}: {n:,} linhas atualizadas")
                updated_total += n

        conn.commit()
        print(f"\nTotal atualizado: {updated_total:,} linhas. Tag agora = nome operacional.")

    # ── Verificação de duplicatas após o update ───────────────────────────────
    print("\nVerificando duplicatas (mesma chave: day_ref+hour_ref+instrument+metric_name)...")
    cur.execute("""
        SELECT day_ref, hour_ref, instrument, metric_name, COUNT(*) as cnt
        FROM measurements_curated
        WHERE row_kind = 'hourly'
          AND instrument IN ({})
        GROUP BY day_ref, hour_ref, instrument, metric_name
        HAVING COUNT(*) > 1
        LIMIT 10
    """.format(",".join("?" * len(INSTRUMENT_ENTITY))),
    list(INSTRUMENT_ENTITY.keys()))

    dupes = cur.fetchall()
    if not dupes:
        print("  Nenhuma duplicata encontrada. Banco limpo.")
    else:
        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT day_ref, hour_ref, instrument, metric_name
                FROM measurements_curated
                WHERE row_kind = 'hourly'
                  AND instrument IN ({})
                GROUP BY day_ref, hour_ref, instrument, metric_name
                HAVING COUNT(*) > 1
            )
        """.format(",".join("?" * len(INSTRUMENT_ENTITY))),
        list(INSTRUMENT_ENTITY.keys()))
        total_dupe_keys = cur.fetchone()[0]
        print(f"  Encontradas {total_dupe_keys:,} chaves com dados duplicados.")
        print("  Exemplos:")
        for row in dupes:
            print(f"    {row[0]} hora {row[1]:>2} | {row[2]:12s} | {row[3]:20s} | {row[4]} cópias")

        if not args.delete_dupes:
            print("\nPara remover as duplicatas, execute com --apply-update --delete-dupes")
        else:
            # Remove duplicatas: mantém a linha com run_id MAIOR (importação mais recente)
            print("\nRemovendo duplicatas (mantém run_id mais alto)...")
            cur.execute("""
                DELETE FROM measurements_curated
                WHERE id IN (
                    SELECT id FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY day_ref, hour_ref, instrument, metric_name
                                   ORDER BY run_id DESC, id DESC
                               ) AS rn
                        FROM measurements_curated
                        WHERE row_kind = 'hourly'
                          AND instrument IN ({})
                    ) ranked
                    WHERE rn > 1
                )
            """.format(",".join("?" * len(INSTRUMENT_ENTITY))),
            list(INSTRUMENT_ENTITY.keys()))
            deleted = cur.rowcount
            conn.commit()
            print(f"  {deleted:,} linhas duplicadas removidas. Banco limpo.")

    conn.close()
    print("\nConcluído.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
