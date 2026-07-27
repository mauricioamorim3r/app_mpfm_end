from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
RAW_DIR = DATA_DIR / 'raw'
EXPORTS_DIR = DATA_DIR / 'exports'
DB_PATH = DATA_DIR / 'sgmed_inspector.db'
DATABASE_URL = f'sqlite:///{DB_PATH.as_posix()}'


def ensure_directories() -> None:
    for directory in (DATA_DIR, RAW_DIR, EXPORTS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
