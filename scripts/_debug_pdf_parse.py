"""
Compara parse de um PDF do dia 14 vs dia 15 de B15 hourly.
Mostra diferenças de texto bruto e resultado do parse_pdf.
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mpfm_engine import flat_text, parse_pdf

folder = r'C:\Users\MAUAM\OneDrive - Equinor\Desktop\DPB FPSO Bacalhau - Metering - 3.2 Daily Reports\3.2.6_18-FT-1106  PW_104DA - Subsea B15\2026\Abr-26\HOURLY'

p14 = os.path.join(folder, 'B15_MPFM_Hourly-20260414-010000+0000.pdf')
p15 = os.path.join(folder, 'B15_MPFM_Hourly-20260415-010000+0000.pdf')

def show_parse(label, path):
    print(f"\n{'='*70}")
    print(f"  {label}: {os.path.basename(path)}")
    print(f"{'='*70}")
    text = flat_text(path)
    print(f"\n--- TEXTO (primeiros 600 chars) ---")
    print(text[:600])
    print(f"\n--- REGEX 'Hourly Report from' ---")
    hm = re.search(r'Hourly Report from\s+([\d.]+)\s+([\d:]+)\s+to\s+([\d.]+)\s+([\d:]+)', text)
    if hm:
        print(f"  MATCH: '{hm.group(0)}'")
    else:
        print("  NAO ENCONTRADO!")
        # Mostra contexto para debug
        idx = text.find('Hourly Report')
        if idx >= 0:
            print(f"  Contexto 'Hourly Report': '{text[idx:idx+80]}'")
        idx2 = text.find('from')
        if idx2 >= 0:
            print(f"  Contexto 'from' (primeiro): '{text[idx2:idx2+80]}'")
    
    from mpfm_engine import TAG_RE
    tags_found = list(TAG_RE.finditer(text))
    print(f"\n--- TAG_RE matches ---")
    if tags_found:
        for t in tags_found:
            print(f"  TAG: '{t.group(1)}'  FT: '{t.group(2)}'")
    else:
        print("  NENHUMA TAG ENCONTRADA!")
        # Tenta encontrar padrões próximos
        for m in re.finditer(r'(PW|PE_|Riser)[^\n]{0,40}Production', text[:2000], re.IGNORECASE):
            print(f"  Candidato: '{m.group(0)}'")
    
    print(f"\n--- parse_pdf resultado ---")
    rec = parse_pdf(path, 'hourly')
    print(f"  hour:      {rec['hour']}")
    print(f"  date_from: {rec['date_from']}")
    print(f"  dt_from:   {rec['dt_from']}")
    print(f"  dt_to:     {rec['dt_to']}")
    print(f"  tags:      {list(rec['tags'].keys())}")
    if rec['tags']:
        tag0 = list(rec['tags'].values())[0]
        print(f"  metrics[0] corr: {tag0['metrics']['mpfm_corr']}")

show_parse("DIA 14", p14)
show_parse("DIA 15", p15)
