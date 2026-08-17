#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para listar arquivos mais recentes dos relatórios diários MPFM
"""

import os
import re
from pathlib import Path
from datetime import datetime

def is_recent_file(path: Path, days_threshold: int = 30) -> bool:
    """Verifica se o arquivo foi modificado recentemente"""
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        days_diff = (datetime.now() - mtime).days
        return days_diff <= days_threshold
    except:
        return False

def is_valid_mpfm_pdf(path: Path) -> bool:
    """Verifica se é um PDF MPFM válido"""
    upper_name = path.name.upper()
    return path.suffix.lower() == ".pdf" and ("MPFM_DAILY" in upper_name or "MPFM_HOURLY" in upper_name)

def main():
    # Caminho da pasta de relatórios (atualizado: nova estrutura "3.1 Registros Diarios MPFM")
    root_path = Path(r"C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3.1 Registros Diarios MPFM")

    if not root_path.exists():
        print(f"Erro: Pasta não encontrada: {root_path}")
        return 1

    print(f"Analisando pasta: {root_path}")
    print("Procurando arquivos MPFM recentes (últimos 30 dias)...")

    # Listar todos os arquivos PDF válidos
    recent_files = []
    for path in root_path.rglob("*.pdf"):
        if is_valid_mpfm_pdf(path) and is_recent_file(path, 30):
            recent_files.append(path)

    if not recent_files:
        print("Nenhum arquivo MPFM recente encontrado.")
        return 0

    print(f"Encontrados {len(recent_files)} arquivos recentes:")

    # Agrupar por pasta
    by_folder = {}
    for path in recent_files:
        folder = path.parent.name
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].append(path)

    # Mostrar resumo
    for folder, files in sorted(by_folder.items()):
        print(f"\n📁 {folder}: {len(files)} arquivos")
        for path in sorted(files, key=lambda x: x.name):
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            print(f"   📄 {path.name} (modificado: {mtime.strftime('%Y-%m-%d %H:%M')})")

    print("\n✅ Análise concluída!")
    print(f"Total de arquivos encontrados: {len(recent_files)}")

    # Salvar lista em arquivo
    with open("recent_files_found.txt", "w", encoding="utf-8") as f:
        f.write(f"Análise realizada em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Pasta analisada: {root_path}\n")
        f.write(f"Total de arquivos: {len(recent_files)}\n\n")

        for folder, files in sorted(by_folder.items()):
            f.write(f"{folder}: {len(files)} arquivos\n")
            for path in sorted(files, key=lambda x: x.name):
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                f.write(f"  {path.name} ({mtime.strftime('%Y-%m-%d %H:%M')})\n")
            f.write("\n")

    print("Lista salva em: recent_files_found.txt")
    return 0

if __name__ == "__main__":
    exit(main())