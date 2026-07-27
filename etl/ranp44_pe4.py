"""Módulo principal ETL RANP 44 - PE-4 Relatório Semestral MPFM.

Gera relatório de desempenho semestral para medidor PE_4 conforme RANP 44 item 8.5.

Uso:
    python -m etl.ranp44_pe4 --well PE_4 --days 180 --end-date 2026-07-08
    python -m etl.ranp44_pe4 --config pacote_vscode_pe4_ranp44/02_CONFIG_RANP44_PE4.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml

from etl.sources.drive_excel import (
    load_mpfm_monthly_files,
    normalize_mpfm_fields,
    aggregate_to_daily,
)
from etl.validate.ranp44_rules import (
    validate_ranp44,
    apply_quality_status,
    generate_audit_log,
)
from etl.export.excel_writer import write_to_template, create_summary_sheet


@dataclass
class JobConfig:
    """Configuração do job ETL."""
    
    well: str = "PE_4"
    days: int = 180
    end_date: date | None = None
    template_path: Path = Path("pacote_vscode_pe4_ranp44/Registro_Desempenho_Semestral_MPFM_RANP44.xlsx")
    output_path: Path | None = None
    source_dir: Path = Path("pacote_vscode_pe4_ranp44")
    master_sheet: str = "05_Historico_Diario_180d"
    first_data_row: int = 6
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> JobConfig:
        """Carrega configuração de arquivo YAML."""
        with open(yaml_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        job = config.get("job", {})
        excel = config.get("excel_template", {})
        
        end_date = job.get("end_date")
        if end_date and isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        template_path = Path(excel.get("path", "Template_Relatorio_Desempenho_Semestral_MPFM_RANP44.xlsx"))
        
        return cls(
            well=job.get("well", "PE_4"),
            days=job.get("days", 180),
            end_date=end_date,
            template_path=template_path,
            master_sheet=excel.get("master_sheet", "05_Historico_Diario_180d"),
            first_data_row=excel.get("first_data_row", 6),
        )
    
    def resolve_paths(self) -> None:
        """Resolve caminhos relativos e define output automático."""
        if not self.template_path.is_absolute():
            # Buscar em diretórios comuns
            search_dirs = [
                Path.cwd(),
                Path.cwd() / "pacote_vscode_pe4_ranp44",
                Path.cwd() / "data",
            ]
            for search_dir in search_dirs:
                candidate = search_dir / self.template_path
                if candidate.exists():
                    self.template_path = candidate
                    break
        
        # Output automático se não especificado
        if self.output_path is None:
            end_str = (self.end_date or date.today()).strftime("%Y%m%d")
            self.output_path = Path(f"Relatorio_Desempenho_Semestral_MPFM_{self.well}_{end_str}.xlsx")


def window_dates(end_date: date, days: int = 180) -> list[date]:
    """Gera lista de datas da janela (180 dias retroativos)."""
    start = end_date - timedelta(days=days - 1)
    return [start + timedelta(days=i) for i in range(days)]


def run_etl(config: JobConfig) -> dict:
    """Executa pipeline ETL completo.
    
    Args:
        config: Configuração do job
        
    Returns:
        Dicionário com resultado da execução
    """
    print("=" * 80)
    print("🚀 ETL RANP 44 - Relatório Semestral MPFM")
    print("=" * 80)
    print(f"Poço: {config.well}")
    print(f"Período: {config.days} dias")
    print(f"Data final: {config.end_date or 'hoje'}")
    print(f"Template: {config.template_path}")
    print(f"Saída: {config.output_path}")
    print("=" * 80)
    
    # Resolver caminhos
    config.resolve_paths()
    
    # Determinar data final
    end_date = config.end_date or date.today()
    expected_dates = window_dates(end_date, config.days)
    
    print(f"\n📅 Janela: {expected_dates[0]} a {expected_dates[-1]} ({len(expected_dates)} dias)")
    
    # ========== ETAPA 1: LEITURA ==========
    print("\n" + "=" * 80)
    print("📂 ETAPA 1: LEITURA DE DADOS")
    print("=" * 80)
    
    try:
        df_raw = load_mpfm_monthly_files(
            source_dir=config.source_dir,
            well=config.well,
            granularity=None,  # Ler DAILYS e RECON
        )
    except Exception as e:
        print(f"❌ Erro ao ler arquivos: {e}")
        return {"success": False, "error": str(e)}
    
    print(f"\n✅ Dados carregados: {len(df_raw)} linhas")
    
    # ========== ETAPA 2: TRANSFORMAÇÃO ==========
    print("\n" + "=" * 80)
    print("⚙️  ETAPA 2: TRANSFORMAÇÃO")
    print("=" * 80)
    
    # Normalizar campos
    df_normalized = normalize_mpfm_fields(df_raw)
    print(f"✅ Campos normalizados: {len(df_normalized)} linhas")
    
    # Agregar para diário
    df_daily = aggregate_to_daily(df_normalized)
    print(f"✅ Agregação diária: {len(df_daily)} dias únicos")
    
    # ========== ETAPA 3: JANELA E COMPLETUDE ==========
    print("\n" + "=" * 80)
    print("📊 ETAPA 3: JANELA DE 180 DIAS")
    print("=" * 80)
    
    # Criar DataFrame com 180 datas
    df_window = pd.DataFrame({"ProductionDate": expected_dates})
    
    # Merge com dados disponíveis
    df_final = df_window.merge(df_daily, on="ProductionDate", how="left")
    print(f"✅ Janela completa: {len(df_final)} linhas (180 esperadas)")
    print(f"   • Dias com dados: {df_final['Massa_oleo_MPFM_t'].notna().sum()}")
    print(f"   • Dias sem dados: {df_final['Massa_oleo_MPFM_t'].isna().sum()}")
    
    # ========== ETAPA 4: VALIDAÇÃO ==========
    print("\n" + "=" * 80)
    print("✅ ETAPA 4: VALIDAÇÃO RANP 44")
    print("=" * 80)
    
    validation = validate_ranp44(df_final, expected_dates, config.well)
    print("\n" + validation.summary())
    
    # Aplicar status de qualidade
    df_final = apply_quality_status(df_final, validation)
    
    # ========== ETAPA 5: AUDITORIA ==========
    print("\n" + "=" * 80)
    print("📋 ETAPA 5: LOG DE AUDITORIA")
    print("=" * 80)
    
    audit_log = generate_audit_log(df_final, validation, config.well, config.days)
    
    # Salvar log em JSON
    log_path = config.output_path.with_suffix(".log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(audit_log, f, indent=2, ensure_ascii=False, default=str)
    print(f"✅ Log salvo: {log_path}")
    
    # ========== ETAPA 6: EXPORTAÇÃO ==========
    print("\n" + "=" * 80)
    print("📝 ETAPA 6: EXPORTAÇÃO PARA EXCEL")
    print("=" * 80)
    
    try:
        write_to_template(
            df=df_final,
            template_path=config.template_path,
            output_path=config.output_path,
            well=config.well,
            master_sheet=config.master_sheet,
            first_data_row=config.first_data_row,
        )
    except PermissionError as e:
        print(f"❌ {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"❌ Erro ao escrever Excel: {e}")
        return {"success": False, "error": str(e)}
    
    # ========== RESUMO FINAL ==========
    print("\n" + "=" * 80)
    print("🎉 ETL CONCLUÍDO COM SUCESSO")
    print("=" * 80)
    print(f"📄 Relatório: {config.output_path}")
    print(f"📋 Log: {log_path}")
    print(f"✅ Validação: {'APROVADA' if validation.is_valid else '❌ BLOQUEADA'}")
    print(f"📊 Dados válidos: {audit_log.get('datas_validas', 0)}/180 dias")
    
    if not validation.is_valid:
        print(f"\n⚠️  ATENÇÃO: Relatório contém {len(validation.blocking_errors)} bloqueios críticos")
        print("   Revisar dados antes de submeter à ANP")
    
    return {
        "success": True,
        "output_file": str(config.output_path),
        "log_file": str(log_path),
        "validation_passed": validation.is_valid,
        "audit_log": audit_log,
    }


def main():
    """Ponto de entrada CLI."""
    parser = argparse.ArgumentParser(
        description="ETL RANP 44 - Relatório Semestral MPFM PE-4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Usando parâmetros diretos
  python -m etl.ranp44_pe4 --well PE_4 --days 180 --end-date 2026-07-08
  
  # Usando arquivo de configuração YAML
  python -m etl.ranp44_pe4 --config pacote_vscode_pe4_ranp44/02_CONFIG_RANP44_PE4.yaml
  
  # Sobrescrever parâmetros do YAML
  python -m etl.ranp44_pe4 --config config.yaml --end-date 2026-07-08
        """,
    )
    
    parser.add_argument("--config", type=Path, help="Arquivo YAML de configuração")
    parser.add_argument("--well", default="PE_4", help="Nome do poço (padrão: PE_4)")
    parser.add_argument("--days", type=int, default=180, help="Número de dias (padrão: 180)")
    parser.add_argument(
        "--end-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        help="Data final (YYYY-MM-DD, padrão: hoje)",
    )
    parser.add_argument("--template", type=Path, help="Caminho do template Excel")
    parser.add_argument("--output", type=Path, help="Caminho do arquivo de saída")
    parser.add_argument("--source-dir", type=Path, default=Path("pacote_vscode_pe4_ranp44"), help="Diretório com arquivos MPFM_parte*.xlsx")
    
    args = parser.parse_args()
    
    # Carregar configuração
    if args.config:
        print(f"📄 Carregando configuração: {args.config}")
        config = JobConfig.from_yaml(args.config)
    else:
        config = JobConfig()
    
    # Sobrescrever com argumentos CLI (se fornecidos)
    if args.well:
        config.well = args.well
    if args.days:
        config.days = args.days
    if args.end_date:
        config.end_date = args.end_date
    if args.template:
        config.template_path = args.template
    if args.output:
        config.output_path = args.output
    if args.source_dir:
        config.source_dir = args.source_dir
    
    # Executar ETL
    try:
        result = run_etl(config)
        
        if result["success"]:
            print("\n✅ Processamento concluído com sucesso!")
            sys.exit(0)
        else:
            print(f"\n❌ Erro: {result.get('error', 'Desconhecido')}")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Execução interrompida pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
