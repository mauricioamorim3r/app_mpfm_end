# Prompt para VSCode — Coleta PE-4 para Relatório Semestral MPFM RANP 44

Você está trabalhando na aplicação que armazena dados diários e horários dos sistemas de medição multifásicos. Implemente um módulo ETL específico para preencher o arquivo `Template_Relatorio_Desempenho_Semestral_MPFM_RANP44.xlsx`, limitado ao escopo do poço `PE_4`, com janela móvel/regulatória de `180 dias`.

## Objetivo
Coletar, validar, consolidar e exportar os dados necessários para o relatório semestral de avaliação/verificação de desempenho do sistema de medição multifásico, conforme RANP 44, preenchendo a aba fonte-mestre `05_Historico_Diario_180d` e as abas cadastrais/evidenciais do template semestral.

## Escopo obrigatório
- Poço: `PE_4`.
- Janela: 180 dias corridos, incluindo a data final configurada pelo usuário.
- Granularidades: diária para relatório e horária para validação/condições de contorno.
- Fontes primárias: banco da aplicação/historiador já organizado.
- Fontes complementares: arquivos Excel recentes no Google Drive com dados MPFM/RECON e dados derivados dos XML ANP tipo 042.
- Saída: workbook preenchido `Relatorio_Desempenho_Semestral_MPFM_PE4_<YYYYMMDD>.xlsx` e pacote de evidências com logs de importação/validação.

## Regra de fonte-mestre
A aba `05_Historico_Diario_180d` é a fonte-mestre operacional do período. As abas `06_FR_Diario`, `07_FR_Semanal`, `08_FR_Mensal`, `09_Condicoes_Contorno` e `13_Resultados_Conclusoes` devem consumir dados dessa aba, sem redigitação manual.

## Requisitos regulatórios mínimos a cobrir
Preencher dados que atendam aos blocos do item 8.5 da RANP 44: identificação do relatório, data, modelo/número de série, período, condições de contorno, propriedades dos fluidos, limites de desvio, dados PVT, versão de software, histórico de 180 dias, resultados e conclusões, plano de ação, plano de contingência, observações complementares e responsáveis. Calcular fatores de reconciliação em base diária, semanal e mensal conforme item 8.5.1.

## Fontes de dados esperadas
1. `app_db` ou camada equivalente da aplicação:
   - dados horários MPFM PE_4;
   - dados diários MPFM PE_4;
   - dados reconciliados/RECON PE_4;
   - eventos, alarmes, flags e qualidade de dados;
   - cadastro de MPFM, TAG, serial, software, PVT e configuração.
2. Google Drive:
   - arquivos mensais `MPFM_*.xlsx` com linhas `Daily` e `Recon`;
   - arquivos Excel dos XML ANP tipo `042`;
   - arquivos de rota/PI/AF PE_4;
   - laudos, certificados, PVT, cromatografia e evidências.

## Implementação esperada
Crie um módulo com estas entradas:
```bash
python -m etl.ranp44_pe4 \
  --template Template_Relatorio_Desempenho_Semestral_MPFM_RANP44.xlsx \
  --output Relatorio_Desempenho_Semestral_MPFM_PE4_20260708.xlsx \
  --well PE_4 \
  --end-date 2026-07-08 \
  --days 180 \
  --drive-folder <id-ou-path> \
  --prefer-app-db true
```

## Regras de seleção de dados
- Filtrar `Entity == PE_4` ou `Well == PE_4` ou tag equivalente do PE_4.
- Não misturar PE_4 com `PW-104DA`, `PE_2`, risers ou outros medidores.
- Quando existir dado horário e diário para o mesmo parâmetro, usar diário para totalizações e horário para min/máx/média/estabilidade.
- Quando existir dado do app e dado do Excel do Drive, priorizar app se tiver trilha de origem; usar Drive como complemento ou validação cruzada.
- Quando houver divergência entre app e XML 042/ANP, registrar em `15_Fontes_Evidencias` e `12_Acao_Contingencia`.

## Preenchimento mínimo do Excel
Preencha:
- `01_Identificacao`: código, revisão, data, natureza, ativo/campo/unidade, sistema avaliado, operador, responsável.
- `02_MPFM_Sistema`: MPFM PE_4, modelo, TAG, serial, versão de software/configuração, PVT e referência.
- `03_Periodo_Escopo`: data inicial/final, dias esperados, dias válidos, completude.
- `04_Criterios_Limites`: limites oficiais do plano/procedimento; não inferir limites sem fonte formal.
- `05_Historico_Diario_180d`: uma linha por dia, com massas, volumes, FR, desvios, condições de contorno e fonte.
- `10_PVT_Software_Fluidos`: PVT, cromatografia, densidades, BSW, viscosidade, software e evidências.
- `11_Referencia_Incerteza`: referência autorizada, certificado, validade, incerteza por fase.
- `12_Acao_Contingencia`: eventos, falhas, plano de ação e contingência.
- `15_Fontes_Evidencias`: link/caminho dos arquivos usados, data, responsável e status.

## Validações obrigatórias
1. A janela deve ter exatamente 180 datas esperadas.
2. Cada data deve ter no máximo uma linha diária válida em `05_Historico_Diario_180d`.
3. Campos de massa e volume devem ser numéricos e coerentes com unidade declarada.
4. `M_HC = M_oleo + M_gas`; `M_total = M_HC + M_agua`.
5. FR = Referência / MPFM; desvio = (MPFM - Referência) / Referência.
6. Se referência estiver ausente, classificar dia como `PARCIAL` ou `DIAGNOSTICO`, não como `OK`.
7. Se critério oficial estiver ausente, não classificar conformidade automaticamente.
8. Se houver falta de dados, preencher `Status_dados` e registrar motivo.
9. Gerar log de auditoria com contagem de linhas por fonte, datas faltantes, duplicidades, unidades e divergências.

## Entregáveis do código
- `etl/ranp44_pe4.py`: orquestração do ETL.
- `etl/sources/drive_excel.py`: leitura dos arquivos Excel do Google Drive.
- `etl/sources/app_db.py`: leitura da base da aplicação.
- `etl/sources/xml042.py`: normalização dos dados extraídos dos XML 042.
- `etl/transform/pe4_mapping.py`: mapeamento para `05_Historico_Diario_180d`.
- `etl/validate/ranp44_rules.py`: validações RANP/qualidade.
- `etl/export/excel_writer.py`: preenchimento do template.
- `tests/test_ranp44_pe4.py`: testes unitários de janela, FR, desvios e duplicidades.

## Critério de pronto
O código estará pronto quando:
- gerar workbook preenchido sem quebrar fórmulas;
- gerar log de validação;
- preencher no mínimo a aba `05_Historico_Diario_180d` e metadados principais;
- sinalizar pendências em vez de mascará-las;
- permitir auditoria de origem por dia e por campo.
