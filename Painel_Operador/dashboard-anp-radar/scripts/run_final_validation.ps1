$ErrorActionPreference = 'Stop'
python scripts/generate_ingestion_template.py
python scripts/validate_ingestion_template.py
python -m unittest discover -s tests -v
python scripts/build_dashboard_data.py
python scripts/validate_measurement_models.py
npm run build:frontend
