import hashlib
import re
from datetime import datetime


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    return re.sub(r'[^a-z0-9]+', '_', lowered).strip('_')


def parse_datetime(value: str) -> datetime | None:
    for pattern in ('%d/%m/%y %H:%M:%S', '%m/%d/%y %H:%M:%S'):
        try:
            return datetime.strptime(value.strip(), pattern)
        except ValueError:
            continue
    return None
