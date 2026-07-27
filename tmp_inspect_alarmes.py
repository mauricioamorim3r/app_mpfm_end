import openpyxl
from pathlib import Path
base = Path(r'C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 01 FPSO Bacalhau - Metering Management\02 INTERNAL CONTROL\00_1 - Gestão de Alarmes\2026')
files = sorted(base.glob('*.xlsm'), key=lambda f: f.stat().st_size, reverse=True)
wb = openpyxl.load_workbook(str(files[0]), read_only=True, data_only=True)
ws = wb['AlarmesConsolidado']
rows = list(ws.iter_rows(values_only=True))
for r in rows:
    if any(c is not None for c in r[:12]):
        print([str(c)[:22] if c else None for c in r[:12]])
    if sum(1 for c in r[:3] if c) > 0:
        pass
