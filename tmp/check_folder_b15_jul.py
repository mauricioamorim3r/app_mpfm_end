import os

folder = r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3.1 Registros Diarios MPFM\3.1.6_18-FT-1106 PW_104DA - Subsea B15\2026\07. Julho"

entries = []
for root, dirs, files in os.walk(folder):
    for f in files:
        p = os.path.join(root, f)
        try:
            sz = os.path.getsize(p)
        except OSError:
            sz = -1
        entries.append((sz, p))

entries.sort(reverse=True)
print(f"Total arquivos: {len(entries)}")
print("--- 10 maiores ---")
for sz, p in entries[:10]:
    print(f"{sz/1024:.1f} KB  {p}")

print()
print("--- extensoes ---")
from collections import Counter
ext_counter = Counter(os.path.splitext(p)[1].lower() for _, p in entries)
for ext, n in ext_counter.most_common():
    print(ext, n)

total_size = sum(sz for sz, _ in entries if sz > 0)
print(f"\nTamanho total: {total_size/1024/1024:.1f} MB")
