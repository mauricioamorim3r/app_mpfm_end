from __future__ import annotations

import argparse
import os
import shutil
import zipfile
from pathlib import Path


EXCLUDE_NAMES = {
    "data",
    "dist",
    "build",
    "dist_release",
    ".devcontainer",
    ".git",
    ".firecrawl",
    ".playwright-cli",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    ".venv",
    ".venv-1",
    "venv",
    "output",
    "appwork",
}

EXCLUDE_GLOBS = (
    ".tmp_*",
    "scratch.db*",
    "scratch.txt",
    "testfile",
    "test_*.xlsx",
    "tmp_*.xlsx",
    "tmp_*.json",
    "tmp_*.py",
)


def should_skip(path: Path) -> bool:
    if path.name in EXCLUDE_NAMES:
        return True
    return any(path.match(pattern) for pattern in EXCLUDE_GLOBS)


def build_clean_zip(root: Path, destination: Path) -> Path:
    stage = Path.home() / "AppData" / "Local" / "Temp" / f"{destination.stem}_stage_{os.getpid()}"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    dest_root = stage / "mpfm_app"
    dest_root.mkdir()

    for item in root.iterdir():
        if should_skip(item):
            continue
        target = dest_root / item.name
        if item.is_dir():
            shutil.copytree(item, target, ignore=shutil.ignore_patterns(*EXCLUDE_GLOBS))
        else:
            shutil.copy2(item, target)

    if destination.exists():
        destination.unlink()

    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in dest_root.rglob("*"):
            if should_skip(path):
                continue
            zf.write(path, path.relative_to(stage))

    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--dest", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    dest = Path(args.dest).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    zip_path = build_clean_zip(root, dest)
    stat = zip_path.stat()
    print(zip_path)
    print(stat.st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
