from pathlib import Path

from .config import EXPORTS_DIR, RAW_DIR
from .utils import compute_sha256


def write_bytes(target: Path, payload: bytes) -> tuple[str, int]:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return compute_sha256(payload), len(payload)


def raw_batch_dir(batch_id: int) -> Path:
    return RAW_DIR / f'batch-{batch_id}'


def export_path(name: str) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORTS_DIR / name
