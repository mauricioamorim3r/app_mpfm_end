"""
Extrai dados horárias dos arquivos TXT de separador e gera Excel.

Campos extraídos (conforme imagens):
- ÓLEO/ÁGUA: Pressure (kpa, barg), Temperature, SD, MD, IV, GV, GSV, Mass, NSV, BSW, CPL, CTL
- GÁS: Pressure (kpa_g), Temperature, SD, DT, Gr.vol, St.vol, Mass, Energy, Diff.press, Flowtime

Uso:
    py -3 scripts/extrair_dados_sep_hourly.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import re
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import datetime

SOURCE_DIR = Path("C:/Users/MAUAM/OneDrive - Equinor/DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM/3.1 Registros Diarios MPFM/Zip/Calib PW104DA/Calib PW104DA")


def parse_hourly_txt(txt_path):
    """
    Parse de arquivo TXT horário de separador.
    Retorna dict com campos extraídos.
    """
    with open(txt_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    data = {
        'file': txt_path.name,
        'folder': txt_path.parent.name,
    }

    # Extrai datas (formato padrão e formato de gás)
    match = re.search(r'Start date / time\s+(\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})', content)
    if match:
        data['start_time'] = match.group(1)
    else:
        # Formato alternativo: Period start
        match = re.search(r'Period start\s+(\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})', content)
        if match:
            data['start_time'] = match.group(1)

    match = re.search(r'End date / time\s+(\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})', content)
    if match:
        data['end_time'] = match.group(1)
    else:
        # Formato alternativo: Period end
        match = re.search(r'Period end\s+(\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})', content)
        if match:
            data['end_time'] = match.group(1)

    # Extrai Meter ID
    match = re.search(r'Meter ID\s+(\S+)', content)
    if match:
        data['meter_id'] = match.group(1)

    # Extrai Flow computer
    match = re.search(r'Flow computer\s*(\S+)', content)
    if match:
        data['flow_computer'] = match.group(1).strip()

    # === HOURLY TOTALS ===
    # Indicated (m3)
    match = re.search(r'Indicated\s+m3\s+([\d.]+)', content)
    if match:
        data['IV_m3'] = float(match.group(1))

    # Gross volume (m3)
    match = re.search(r'Gross volume\s+m3\s+([\d.]+)', content)
    if match:
        data['GV_m3'] = float(match.group(1))

    # Mass (tonne)
    match = re.search(r'Mass\s+tonne\s+([\d.]+)', content)
    if match:
        data['Mass_t'] = float(match.group(1))

    # Gross standard volume (sm3)
    match = re.search(r'Gross standard volume\s+sm3\s+([\d.]+)', content)
    if match:
        data['GSV_sm3'] = float(match.group(1))

    # Net standard volume (sm3)
    match = re.search(r'Net standard volume\s+sm3\s+([\d.]+)', content)
    if match:
        data['NSV_sm3'] = float(match.group(1))

    # === FLOW WEIGHTED AVERAGES ===
    # Meter temperature (deg c)
    match = re.search(r'Meter temperature\s+deg c\s+([\d.]+)', content)
    if match:
        data['Temperature_degc'] = float(match.group(1))

    # Meter pressure (kPa(g))
    match = re.search(r'Meter pressure\s+kPa\(g\)\s+([\d.]+)', content)
    if match:
        data['Pressure_kPag'] = float(match.group(1))
        # Converte para barg (1 kPa(g) = 0.01 barg)
        data['Pressure_barg'] = float(match.group(1)) / 100
        # Converte para kPa absoluto (kPa(a) = kPa(g) + 101.325)
        data['Pressure_kpa'] = float(match.group(1)) + 101.325

    # Standard density (kg/sm3)
    match = re.search(r'Standard density\s+kg/sm3\s+([\d.]+)', content)
    if match:
        data['SD_kg_sm3'] = float(match.group(1))

    # Meter density (kg/m3)
    match = re.search(r'Meter density\s+kg/m3\s+([\d.]+)', content)
    if match:
        data['MD_kg_m3'] = float(match.group(1))

    # BSW (%vol/vol)
    match = re.search(r'BSW\s+%vol/vol\s+([\d.]+)', content)
    if match:
        data['BSW_pct'] = float(match.group(1))

    # Ctl
    match = re.search(r'Ctl\s+-\s+([\d.]+)', content)
    if match:
        data['CTL'] = float(match.group(1))

    # Cpl
    match = re.search(r'Cpl\s+-\s+([\d.]+)', content)
    if match:
        data['CPL'] = float(match.group(1))

    # Ctpl
    match = re.search(r'Ctpl\s+-\s+([\d.]+)', content)
    if match:
        data['CTPL'] = float(match.group(1))

    # === TIME WEIGHTED AVERAGE FLOW RATES ===
    # Gross volume (m3/h)
    match = re.search(r'Gross volume\s+m3/h\s+([\d.]+)', content)
    if match:
        data['GV_m3h'] = float(match.group(1))

    # Mass (tonne/h)
    match = re.search(r'Mass\s+tonne/h\s+([\d.]+)', content)
    if match:
        data['Mass_th'] = float(match.group(1))

    # Gross std. volume (sm3/h)
    match = re.search(r'Gross std\. volume\s+sm3/h\s+([\d.]+)', content)
    if match:
        data['GSV_sm3h'] = float(match.group(1))

    # Net std. volume (sm3/h)
    match = re.search(r'Net std\. volume\s+sm3/h\s+([\d.]+)', content)
    if match:
        data['NSV_sm3h'] = float(match.group(1))

    # === CAMPOS ESPECÍFICOS DE GÁS ===
    # Base volume (sm3) - equivalente a "St. vol." na imagem
    match = re.search(r'Base volume\s+sm3\s+([\d.]+)', content)
    if match:
        data['Base_volume_sm3'] = float(match.group(1))

    # Base volume flow rate (sm3/h)
    match = re.search(r'Base volume flow rate\s+sm3/h\s+([\d.]+)', content)
    if match:
        data['Base_volume_sm3h'] = float(match.group(1))

    # Energy (GJ)
    match = re.search(r'Energy\s+GJ\s+([\d.]+)', content)
    if match:
        data['Energy_GJ'] = float(match.group(1))

    # Energy flow rate (GJ/h)
    match = re.search(r'Energy flow rate\s+GJ/h\s+([\d.]+)', content)
    if match:
        data['Energy_GJh'] = float(match.group(1))

    # Base density (kg/sm3) - equivalente a SD
    match = re.search(r'Base density\s+kg/sm3\s+([\d.]+)', content)
    if match:
        data['Base_density_kg_sm3'] = float(match.group(1))

    # Differential pressure (kPa)
    match = re.search(r'Differential pressure\s+kPa\s+([\d.]+)', content)
    if match:
        data['Diff_pressure_kPa'] = float(match.group(1))

    # Heating value (MJ/sm3)
    match = re.search(r'Heating value\s+MJ/sm3\s+([\d.]+)', content)
    if match:
        data['Heating_value_MJ_sm3'] = float(match.group(1))

    # Wobbe index (MJ/sm3)
    match = re.search(r'Wobbe index\s+MJ/sm3\s+([\d.]+)', content)
    if match:
        data['Wobbe_index_MJ_sm3'] = float(match.group(1))

    # Relative density
    match = re.search(r'Relative density\s+-\s+([\d.]+)', content)
    if match:
        data['Relative_density'] = float(match.group(1))

    # Specific gravity
    match = re.search(r'Specific gravity\s+-\s+([\d.]+)', content)
    if match:
        data['Specific_gravity'] = float(match.group(1))

    return data


def classify_fluid_type(meter_id):
    """Classifica tipo de fluido baseado no meter ID."""
    mapping = {
        "20FT0247": "OLEO",
        "20FT0251": "AGUA",
        "20FT0244": "GAS",
    }
    return mapping.get(meter_id, "UNKNOWN")


def extract_hour_from_filename(filename):
    """Extrai hora do nome do arquivo."""
    # Run_Hourly1-1.20260827010000.txt -> hora 01
    match = re.search(r'\.(\d{14})\.txt$', filename)
    if match:
        timestamp = match.group(1)
        hour = int(timestamp[8:10])
        return hour
    return None


def main():
    print("=" * 80)
    print("EXTRAÇÃO DE DADOS HORÁRIOS - SEPARADOR")
    print("=" * 80)

    if not SOURCE_DIR.exists():
        print(f"❌ Pasta não encontrada: {SOURCE_DIR}")
        return

    # Escaneia arquivos TXT
    txt_files = sorted(SOURCE_DIR.rglob("*.txt"))

    if not txt_files:
        print(f"⚠️  Nenhum arquivo TXT encontrado")
        return

    print(f"\n📁 Arquivos encontrados: {len(txt_files)}")

    # Processa arquivos
    print(f"\n📊 Processando arquivos...")

    data_by_fluid = {
        "OLEO": [],
        "AGUA": [],
        "GAS": [],
    }

    for txt_path in txt_files:
        try:
            data = parse_hourly_txt(txt_path)
            fluid_type = classify_fluid_type(data.get('meter_id', ''))
            hour = extract_hour_from_filename(data['file'])

            if hour is not None:
                data['hour'] = hour

            if fluid_type != "UNKNOWN":
                data_by_fluid[fluid_type].append(data)
                print(f"   ✓ {txt_path.name} → {fluid_type} h{hour:02d}")
            else:
                print(f"   ⚠️  {txt_path.name} → Meter ID desconhecido")

        except Exception as e:
            print(f"   ❌ Erro ao processar {txt_path.name}: {e}")

    # Gera Excel
    print(f"\n📝 Gerando Excel...")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    center_align = Alignment(horizontal='center', vertical='center')

    for fluid_type in ["OLEO", "AGUA", "GAS"]:
        data_list = data_by_fluid[fluid_type]

        if not data_list:
            print(f"   ⚠️  Sem dados para {fluid_type}")
            continue

        ws = wb.create_sheet(title=fluid_type)

        # Cabeçalho baseado nas imagens
        if fluid_type in ["OLEO", "AGUA"]:
            headers = [
                "Hora", "Start Time", "End Time", "Meter ID", "Flow Computer",
                "Pressure (kpa)", "Pressure (barg)", "Temperature (deg c)",
                "SD (kg/sm³)", "MD (kg/m³)", "IV (m³)", "GV (m³)", "GSV (sm³)",
                "Mass (t)", "NSV (sm³)", "BSW (%)", "CPL", "CTL"
            ]
            fields = [
                'hour', 'start_time', 'end_time', 'meter_id', 'flow_computer',
                'Pressure_kpa', 'Pressure_barg', 'Temperature_degc',
                'SD_kg_sm3', 'MD_kg_m3', 'IV_m3', 'GV_m3', 'GSV_sm3',
                'Mass_t', 'NSV_sm3', 'BSW_pct', 'CPL', 'CTL'
            ]
        else:  # GAS
            headers = [
                "Hora", "Start Time", "End Time", "Meter ID", "Flow Computer",
                "Pressure (kpa_g)", "Temperature (deg c)",
                "SD (kg/sm³)", "DT (kg/m³)", "Gr. vol. (m³)", "St. vol. (sm³)",
                "Mass (t)", "Energy (GJ)", "Diff. press. (kPa)",
                "Heating value (MJ/sm³)", "Wobbe index (MJ/sm³)",
                "Relative density", "Specific gravity"
            ]
            fields = [
                'hour', 'start_time', 'end_time', 'meter_id', 'flow_computer',
                'Pressure_kPag', 'Temperature_degc',
                'Base_density_kg_sm3', 'MD_kg_m3', 'GV_m3', 'Base_volume_sm3',
                'Mass_t', 'Energy_GJ', 'Diff_pressure_kPa',
                'Heating_value_MJ_sm3', 'Wobbe_index_MJ_sm3',
                'Relative_density', 'Specific_gravity'
            ]

        # Escreve cabeçalho
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align

        # Escreve dados
        for row_idx, data_dict in enumerate(sorted(data_list, key=lambda x: x.get('hour', 0)), 2):
            for col_idx, field in enumerate(fields, 1):
                value = data_dict.get(field, '')
                ws.cell(row=row_idx, column=col_idx).value = value

        # Ajusta larguras
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width

        print(f"   ✓ Aba {fluid_type}: {len(data_list)} linhas")

    # Salva Excel
    output_file = "AUTOMACAO_HTML/HTML_GERADOS/SEPARADOR_HOURLY_27_08_2026.xlsx"
    wb.save(output_file)

    print(f"\n✅ Excel gerado: {output_file}")
    print(f"   Tamanho: {Path(output_file).stat().st_size / 1024:.1f} KB")

    print("\n" + "=" * 80)
    print("✅ EXTRAÇÃO CONCLUÍDA!")
    print("=" * 80)
    print("\n💡 Próximos passos:")
    print(f"   1. Abrir o Excel: {output_file}")
    print(f"   2. Validar os dados extraídos")
    print(f"   3. Importar no sistema se necessário")


if __name__ == "__main__":
    main()
