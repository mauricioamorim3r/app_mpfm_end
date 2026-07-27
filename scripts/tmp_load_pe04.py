import sys
import time
import subprocess
from pathlib import Path

def run_import():
    base_dir = Path(r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3. Registros de Operação SGM Multifasico\3.1 Registros Diarios MPFM\3.1.4_18-FT-1506 PE 4 - Subsea B05\2026")
    
    # Months from July down to February
    months = [
        "06. Junho",
        "05. Maio",
        "04. Abril",
        "03. Março",
        "02. Fevereiro"
    ]
    
    # Removed static script_path definition
    
    for month in months:
        month_path = base_dir / month
        if not month_path.exists():
            print(f"Skipping {month_path}, does not exist.")
            continue
            
        for folder_type in ["Daily", "Hourly"]:
            target_folder = month_path / folder_type
            if target_folder.exists():
                print(f"\n======================================")
                print(f"Loading {month} - {folder_type}")
                print(f"Target: {target_folder}")
                print(f"======================================")
                
                if folder_type == "Daily":
                    script_path = r"C:\Users\MAUAM\OneDrive - Equinor\Desktop\NOVO\scripts\repair_missing_mpfm_daily_from_folder.py"
                else:
                    script_path = r"C:\Users\MAUAM\OneDrive - Equinor\Desktop\NOVO\scripts\repair_missing_mpfm_hourly_from_folder.py"
                
                cmd = [sys.executable, script_path, "--bank", "B05", "--folder", str(target_folder)]
                
                print(f"Running command: {' '.join(cmd)}")
                subprocess.run(cmd)
                
                print(f"Finished {month} - {folder_type}. Pausing for 5 seconds...")
                time.sleep(5)
            else:
                print(f"Folder not found: {target_folder}")

if __name__ == "__main__":
    run_import()
