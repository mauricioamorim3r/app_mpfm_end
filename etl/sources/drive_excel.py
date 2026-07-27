"""Leitura de arquivos Excel MPFM (Drive mensais)."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import pandas as pd


ENTITY_FILTER = ["PE_4"]
EXCLUDE_ENTITIES = ["PE_2", "PW-104DA", "Riser_P4", "Riser_P5", "Riser_P2"]


def load_mpfm_monthly_files(
    source_dir: Path,
    well: str = "PE_4",
    granularity: Literal["DAILYS", "RECON", "HOURLYS"] | None = None,
) -> pd.DataFrame:
    """Carrega e concatena todos MPFM_parte*.xlsx de um diretório.
    
    Args:
        source_dir: Diretório contendo os arquivos MPFM_parte*.xlsx
        well: Poço para filtrar (padrão PE_4)
        granularity: Aba específica a ler (DAILYS, RECON, HOURLYS) ou None para todas
        
    Returns:
        DataFrame consolidado com todos os dados
    """
    files = sorted(source_dir.glob("MPFM_parte*.xlsx"))
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo MPFM_parte*.xlsx encontrado em {source_dir}")
    
    print(f"📂 Arquivos encontrados: {len(files)}")
    for f in files:
        print(f"   • {f.name}")
    
    frames = []
    sheets_to_read = [granularity] if granularity else ["DAILYS", "RECON"]
    
    for file_path in files:
        for sheet in sheets_to_read:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet)
                df["__source_file"] = file_path.name
                df["__source_sheet"] = sheet
                frames.append(df)
                print(f"   ✓ {file_path.name}/{sheet}: {len(df)} linhas")
            except ValueError as e:
                print(f"   ⚠️  Aba '{sheet}' não encontrada em {file_path.name}: {e}")
            except Exception as e:
                print(f"   ❌ Erro ao ler {file_path.name}/{sheet}: {e}")
    
    if not frames:
        raise ValueError("Nenhum dado lido dos arquivos MPFM")
    
    df_all = pd.concat(frames, ignore_index=True)
    print(f"\n📊 Total antes do filtro: {len(df_all)} linhas")
    
    # Filtro rigoroso PE_4
    df_filtered = filter_pe4_only(df_all, well)
    print(f"📊 Total após filtro {well}: {len(df_filtered)} linhas")
    
    return df_filtered


def filter_pe4_only(df: pd.DataFrame, well: str = "PE_4") -> pd.DataFrame:
    """Filtra estritamente apenas dados do poço especificado.
    
    Exclui Risers, PE_2, PW-104DA e outros medidores.
    """
    if df.empty:
        return df
    
    # Identifica coluna de entidade/poço
    entity_col = None
    for col in ["Entity", "Well", "Poço", "Poco", "Tag"]:
        if col in df.columns:
            entity_col = col
            break
    
    if not entity_col:
        print(f"⚠️  Nenhuma coluna Entity/Well encontrada. Colunas: {df.columns.tolist()[:10]}")
        return df
    
    # Filtro positivo (incluir apenas PE_4)
    mask = df[entity_col].astype(str).str.upper() == well.upper()
    
    # Filtro negativo (excluir explicitamente)
    for exclude in EXCLUDE_ENTITIES:
        mask_exclude = df[entity_col].astype(str).str.upper() == exclude.upper()
        mask = mask & (~mask_exclude)
    
    df_out = df.loc[mask].copy()
    
    # Log de exclusões
    excluded = len(df) - len(df_out)
    if excluded > 0:
        entities_excluded = df.loc[~mask, entity_col].value_counts().to_dict()
        print(f"   🚫 Excluídos {excluded} registros:")
        for entity, count in list(entities_excluded.items())[:5]:
            print(f"      • {entity}: {count} linhas")
    
    return df_out


def normalize_mpfm_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza campos MPFM para schema RANP44.
    
    Mapeia colunas dos Excel mensais para campos esperados no template.
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # Normalizar ProductionDate
    if "ProductionDate" in df.columns:
        df["ProductionDate"] = pd.to_datetime(df["ProductionDate"], errors="coerce").dt.date
    
    # Mapear campos de massa MPFM corrigidos
    field_map = {
        "MPFM corr Óleo (t)": "Massa_oleo_MPFM_t",
        "MPFM corr Gás (t)": "Massa_gas_MPFM_t",
        "MPFM corr Água (t)": "Massa_agua_MPFM_t",
        "MPFM corr HC (t)": "Massa_HC_MPFM_t",
        "MPFM corr Total (t)": "Massa_Total_MPFM_t",
        # Campos RECON para referência
        "Recon Daily Óleo (t)": "Massa_oleo_REF_t",
        "Recon Daily Gás (t)": "Massa_gas_REF_t",
        "Recon Daily Água (t)": "Massa_agua_REF_t",
        # Volumes
        "PVT vol Óleo (m³)": "Volume_oleo_MPFM_Sm3",
        "PVT vol Gás (Sm³)": "Volume_gas_MPFM_Sm3",
        "PVT vol Água (m³)": "Volume_agua_MPFM_m3",
        # Condições de contorno
        "Pressão (barg)": "Pressao_bar",
        "Temperatura (°C)": "Temperatura_C",
        # Tag
        "Tag": "MPFM_Tag",
        "Instrumento": "MPFM_Tag",
    }
    
    for old_name, new_name in field_map.items():
        if old_name in df.columns and new_name not in df.columns:
            df[new_name] = df[old_name]
    
    # Volume de gás: converter de Sm³ para kSm³
    if "Volume_gas_MPFM_Sm3" in df.columns:
        df["Volume_gas_MPFM_kSm3"] = df["Volume_gas_MPFM_Sm3"] / 1000.0
    
    # Granularity
    if "Granularity" in df.columns:
        df["Granularidade"] = df["Granularity"]
    
    # Metadados de fonte
    df["Fonte_mestre"] = "drive_mpfm_monthly_excel"
    df["Fonte_arquivo"] = df.get("__source_file", "")
    df["Fonte_aba"] = df.get("__source_sheet", "")
    
    return df


def aggregate_to_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega dados horários/RECON para granularidade diária.
    
    Aplica regras de consolidação:
    - Massas: soma
    - Pressão/Temperatura: média/min/max
    - GVF/BSW: média
    """
    if df.empty:
        return df
    
    if "ProductionDate" not in df.columns:
        raise ValueError("Campo ProductionDate não encontrado")
    
    # Campos numéricos para agregação
    mass_fields = [
        "Massa_oleo_MPFM_t",
        "Massa_gas_MPFM_t",
        "Massa_agua_MPFM_t",
        "Massa_oleo_REF_t",
        "Massa_gas_REF_t",
        "Massa_agua_REF_t",
    ]
    
    volume_fields = [
        "Volume_oleo_MPFM_Sm3",
        "Volume_gas_MPFM_kSm3",
        "Volume_agua_MPFM_m3",
    ]
    
    avg_fields = ["Pressao_bar", "Temperatura_C"]
    
    # Agrupar por ProductionDate
    agg_dict = {}
    
    for field in mass_fields + volume_fields:
        if field in df.columns:
            agg_dict[field] = "sum"
    
    for field in avg_fields:
        if field in df.columns:
            agg_dict[field] = "mean"
    
    # Metadados: concatenar arquivos fonte
    if "Fonte_arquivo" in df.columns:
        agg_dict["Fonte_arquivo"] = lambda x: "; ".join(sorted(set(x.dropna().astype(str))))
    
    if "Fonte_aba" in df.columns:
        agg_dict["Fonte_aba"] = lambda x: "; ".join(sorted(set(x.dropna().astype(str))))
    
    if "MPFM_Tag" in df.columns:
        agg_dict["MPFM_Tag"] = "first"
    
    if not agg_dict:
        print("⚠️  Nenhum campo numérico encontrado para agregação")
        return df
    
    df_daily = df.groupby("ProductionDate", dropna=False).agg(agg_dict).reset_index()
    
    # Arredondar valores
    for col in df_daily.columns:
        if df_daily[col].dtype in ["float64", "float32"]:
            df_daily[col] = df_daily[col].round(3)
    
    return df_daily
