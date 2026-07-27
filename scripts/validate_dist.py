"""Quick validation of distribution ZIP."""
import zipfile, json, sys

zip_path = sys.argv[1] if len(sys.argv) > 1 else ""
z = zipfile.ZipFile(zip_path)
names = z.namelist()

checks = ["server.py", "data/mpfm_local.db", "data/cadastro.json",
          "data/user_prefs.json", "COMO_USAR.txt"]
print("=== Arquivos-chave ===")
for c in checks:
    print(f"  {'OK' if c in names else 'FALTA'}: {c}")

bad = [n for n in names if "-lt-" in n or "MPFM_backup_" in n or n.startswith("uploads/")]
print(f"\n=== Arquivos indevidos no ZIP: {len(bad)} ===")
for b in bad:
    print(f"  INDEVIDO: {b}")

prefs = json.loads(z.read("data/user_prefs.json"))
afm = prefs.get("auto_folder_monitor", {})
print(f"\n=== user_prefs.json ===")
print(f"  folders = {afm.get('folders')}")
print(f"  enabled = {afm.get('enabled')}")
print(f"  theme_mode = {prefs.get('theme_mode')}")
print(f"  xml042_cnpj8 = {prefs.get('xml042_cnpj8')}")
raw = z.read("data/user_prefs.json").decode()
print(f"  Paths de maquina? {'SIM - PROBLEMA!' if 'MAUAM' in raw or ('Equinor' in raw and 'equinor' not in raw.lower()) else 'nao'}")

wbs = sorted(n for n in names if n.startswith("data/outputs/") and n.endswith(".xlsx"))
print(f"\n=== Workbooks Excel ({len(wbs)}) ===")
for wb in wbs:
    print(f"  {wb}")

print(f"\nTotal entradas no ZIP: {len(names)}")
z.close()
