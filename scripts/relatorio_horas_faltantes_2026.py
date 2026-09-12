#!/usr/bin/env python3
"""
Relatório de horas faltantes em 2026 para todos os bancos MPFM.

Identifica dias que têm menos de 24 horas de dados importados,
considerando que a hora 23 de cada dia está no arquivo -000000 do dia seguinte.

Uso:
    py -3 scripts/relatorio_horas_faltantes_2026.py
"""
import sys
sys.path.insert(0, '.')

import sqlite3
from app_config import DB_PATH
from datetime import date, timedelta
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

# Bancos a verificar
BANCOS = ['B03', 'B05', 'B08', 'B10', 'B13', 'B15']

# Período a verificar (2026 completo)
DATA_INICIO = date(2026, 1, 1)
DATA_FIM = date(2026, 12, 31)

def verificar_horas_dia(conn, banco, dia_ref):
    """Retorna conjunto de horas disponíveis para um banco/dia."""
    cur = conn.cursor()
    rows = cur.execute('''
        SELECT DISTINCT hour_ref
        FROM measurements_curated
        WHERE bank = ? AND day_ref = ? AND row_kind = 'hourly'
        ORDER BY hour_ref
    ''', (banco, dia_ref)).fetchall()

    horas = {r[0] for r in rows if r[0] is not None}
    return horas

def main():
    conn = sqlite3.connect(DB_PATH)

    print('Verificando horas faltantes em 2026 para todos os bancos...\n')

    # Estrutura: {banco: [(dia, horas_disponiveis, horas_faltantes), ...]}
    resultados = {banco: [] for banco in BANCOS}

    dia_atual = DATA_INICIO
    while dia_atual <= DATA_FIM:
        dia_ref = dia_atual.strftime('%Y-%m-%d')

        for banco in BANCOS:
            horas = verificar_horas_dia(conn, banco, dia_ref)
            horas_esperadas = set(range(24))
            faltantes = horas_esperadas - horas

            if faltantes:
                resultados[banco].append({
                    'dia': dia_ref,
                    'horas_disponiveis': len(horas),
                    'horas_faltantes': sorted(faltantes),
                    'count_faltantes': len(faltantes)
                })

        dia_atual += timedelta(days=1)

    conn.close()

    # Resumo no console
    print('=== RESUMO DE LACUNAS POR BANCO ===\n')
    for banco in BANCOS:
        lacunas = resultados[banco]
        if lacunas:
            total_dias = len(lacunas)
            total_horas = sum(item['count_faltantes'] for item in lacunas)
            print(f'{banco}: {total_dias} dias com lacunas | {total_horas} horas faltantes no total')

            # Mostrar primeiros 5 dias como exemplo
            print(f'  Exemplos:')
            for item in lacunas[:5]:
                print(f'    {item["dia"]}: {item["horas_disponiveis"]}/24 horas | faltam horas {item["horas_faltantes"]}')
            if len(lacunas) > 5:
                print(f'    ... e mais {len(lacunas) - 5} dias')
            print()
        else:
            print(f'{banco}: Nenhuma lacuna encontrada (todos os dias com 24 horas)')
            print()

    # Gerar Excel
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove a sheet default

    header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    center_align = Alignment(horizontal='center', vertical='center')

    for banco in BANCOS:
        ws = wb.create_sheet(title=banco)

        # Cabeçalho
        ws['A1'] = 'Data'
        ws['B1'] = 'Horas Disponíveis'
        ws['C1'] = 'Horas Faltantes'
        ws['D1'] = 'Quais Horas Faltam'

        for col in ['A1', 'B1', 'C1', 'D1']:
            ws[col].fill = header_fill
            ws[col].font = header_font
            ws[col].alignment = center_align

        # Larguras
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 18
        ws.column_dimensions['D'].width = 50

        # Dados
        row = 2
        for item in resultados[banco]:
            ws[f'A{row}'] = item['dia']
            ws[f'B{row}'] = item['horas_disponiveis']
            ws[f'C{row}'] = item['count_faltantes']
            ws[f'D{row}'] = ', '.join(f'h{h:02d}' for h in item['horas_faltantes'])

            # Centralizar
            for col in ['A', 'B', 'C']:
                ws[f'{col}{row}'].alignment = center_align

            row += 1

        # Totais
        if resultados[banco]:
            row += 1
            ws[f'A{row}'] = 'TOTAL'
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'B{row}'] = len(resultados[banco])
            ws[f'B{row}'].font = Font(bold=True)
            ws[f'C{row}'] = sum(item['count_faltantes'] for item in resultados[banco])
            ws[f'C{row}'].font = Font(bold=True)

    output_file = 'AUTOMACAO_HTML/HTML_GERADOS/RELATORIO_HORAS_FALTANTES_2026.xlsx'
    wb.save(output_file)
    print(f'\n✓ Relatório salvo em: {output_file}')

if __name__ == '__main__':
    main()
