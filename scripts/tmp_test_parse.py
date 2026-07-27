import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server

p = Path(r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3. Registros de Operação SGM Multifasico\3.1 Registros Diarios MPFM\3.1.1_13-FT-0367 Riser P5 - Topside B03\2026\01. Janeiro\Daily")

for pdf in sorted(p.glob('*.pdf')):
    rec = server.engine.parse_pdf(str(pdf), 'daily')
    print(pdf.name, "-> date_from:", rec.get('date_from'))

