"""Republica o dashboard HTML oficial a partir do .xlsx já processado."""
from pathlib import Path
import gerar_base_unica_standalone as g

root = Path(__file__).resolve().parent
excel_dir = root / "EXCEL_GERADOS"
html_dir = root / "HTML_GERADOS"
source = (excel_dir / "BASE_UNICA_STANDALONE_20260812_094902.xlsx")
if not source.exists():
    source = root / "BASE_UNICA_STANDALONE_20260812_094902.xlsx"
out = html_dir / "BASE_UNICA_STANDALONE_20260812_094902_STANDALONE_DASHBOARD.html"

frames = g._load_dashboard_source_frames(source)
df = g._normalize_master_columns(frames["BASE_UNICA_STANDALONE"])
days = sorted({str(v)[:10] for v in df["ProductionDate"].dropna() if str(v)[:10] not in ("", "nan")})
g.publish_dashboard(
    out, df, days, days, [], None,
    frames.get(g.ALARM_EVENT_SHEET_NAME), aligned_bank=g.SEP_ALIGNED_BANK,
    preloaded_pi_df=frames.get(g.PI_SHEET_NAME),
    preloaded_comparativo_df=frames.get(g.COMPARATIVO_TOTAL_SHEET_NAME),
    preloaded_alarm_events=frames.get(g.ALARM_EVENT_SHEET_NAME),
    source_workbook_path=source, preloaded_source_frames=frames,
)
print(out)
