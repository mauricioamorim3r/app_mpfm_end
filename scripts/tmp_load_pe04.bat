@echo off
set "BASE_DIR=C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3.1 Registros Diarios MPFM\3.1.4_18-FT-1506 PE 4 e PE_EO105 - Subsea B05\2026"

echo === JULHO ===
python scripts\repair_missing_mpfm_daily_from_folder.py --bank B05 --folder "%BASE_DIR%\07. Julho\Daily"
timeout /t 5
python scripts\repair_missing_mpfm_hourly_from_folder.py --bank B05 --folder "%BASE_DIR%\07. Julho\Hourly"
timeout /t 5

echo === JUNHO ===
python scripts\repair_missing_mpfm_daily_from_folder.py --bank B05 --folder "%BASE_DIR%\06. Junho\Daily"
timeout /t 5
python scripts\repair_missing_mpfm_hourly_from_folder.py --bank B05 --folder "%BASE_DIR%\06. Junho\Hourly"
timeout /t 5

echo === MAIO ===
python scripts\repair_missing_mpfm_daily_from_folder.py --bank B05 --folder "%BASE_DIR%\05. Maio\Daily"
timeout /t 5
python scripts\repair_missing_mpfm_hourly_from_folder.py --bank B05 --folder "%BASE_DIR%\05. Maio\Hourly"
timeout /t 5

echo === ABRIL ===
python scripts\repair_missing_mpfm_daily_from_folder.py --bank B05 --folder "%BASE_DIR%\04. Abril\Daily"
timeout /t 5
python scripts\repair_missing_mpfm_hourly_from_folder.py --bank B05 --folder "%BASE_DIR%\04. Abril\Hourly"
timeout /t 5

echo === MARCO ===
python scripts\repair_missing_mpfm_daily_from_folder.py --bank B05 --folder "%BASE_DIR%\03. Março\Daily"
timeout /t 5
python scripts\repair_missing_mpfm_hourly_from_folder.py --bank B05 --folder "%BASE_DIR%\03. Março\Hourly"
timeout /t 5

echo === FEVEREIRO ===
python scripts\repair_missing_mpfm_daily_from_folder.py --bank B05 --folder "%BASE_DIR%\02. Fevereiro\Daily"
timeout /t 5
python scripts\repair_missing_mpfm_hourly_from_folder.py --bank B05 --folder "%BASE_DIR%\02. Fevereiro\Hourly"
timeout /t 5

echo CONCLUIDO.
