# Analise tecnica da pasta Painel_Operador

Data da analise: 2026-07-03

## Escopo

Pasta analisada: `C:\MPFM\NOVO\Painel_Operador`.

Foram considerados arquivos operacionais, documentos, planilhas, XMLs, TXT, CSV, o app `dashboard-anp-radar` e seus dados consolidados. Para leitura tecnica foram ignorados, quando aplicavel, `node_modules`, `dist`, `release`, `.playwright-mcp` e `__pycache__`, pois sao artefatos de execucao ou empacotamento.

## Volumetria

Inventario bruto relevante:

- 7.271 arquivos, aproximadamente 5,08 GB, incluindo artefatos de transporte e `.git`.
- 4.112 arquivos `.txt`, aproximadamente 16,45 MB.
- 1.872 arquivos `.pdf`, aproximadamente 851,43 MB.
- 165 arquivos `.xlsx`, aproximadamente 43,90 MB.
- 129 arquivos `.xml`, aproximadamente 511,29 MB.
- 66 arquivos `.csv`, aproximadamente 1.198,96 MB.
- 36 arquivos `.zip`, aproximadamente 851,76 MB.
- 11 arquivos `.docx`, aproximadamente 64,63 MB.
- 9 arquivos `.xlsm`, aproximadamente 38,25 MB.

Achado de higiene: existe uma pasta `.git` dentro de `Painel_Operador` com cerca de 1,58 GB. Ela nao deve ser tratada como fonte operacional. Tambem ha `dashboard-anp-radar (2).zip`, `materialcursompfm.zip`, `node_modules`, `dist`, `release` e copias duplicadas em `dashboard-anp-radar/MODELOS`.

## Grandes familias de informacao

### 1. Daily Reports FPSO Bacalhau

Pastas identificadas:

- `FPSO-Bacalhau_Daily reports_2026-06-01`
- `FPSO-Bacalhau_Daily reports_2026-06-02`

Conteudo principal:

- `01 - CV_Reports`: relatorios TXT dos computadores de vazao.
- `03 - IHM_Reports`: planilhas diarias de oleo, gas, agua e balanco de gas.
- `05 - XML`: XMLs fiscais ANP 001, 002 e 003, mais ZIPs correspondentes.

Padroes TXT encontrados:

- `Run_Daily`: 102 arquivos.
- `Run_24Hours`: 102 arquivos.
- `Run_Hourly*`: milhares de arquivos horarios.
- `AlarmsAndEvents_Daily` e `AlarmsAndEvents_Hourly`: eventos e alarmes.
- `Parameters.xml`: snapshots de parametros dos flow computers.
- `Security.xml`: usuarios/permissoes do computador de vazao.

Uso recomendado:

- Reconciliacao raw CV -> XML fiscal.
- Reconstrucao horaria e diaria por computador de vazao.
- Detecção de mudanca de parametro.
- Auditoria de alarmes/eventos por periodo.
- Evidencia para divergencias entre XML, Painel ANP e dados brutos.

### 2. Exports do Painel do Operador ANP

Arquivos principais na raiz:

- `Óleo Linear.xlsx`
- `Gás Linear.xlsx`
- `Gás Diferencial.xlsx`
- `BSW em Linha.xlsx`
- `Falha de Medição.xlsx`

Colunas observadas:

- Oleo linear: instalacao, codigo da instalacao, tag do ponto, inicio/fim do periodo, volume bruto corrigido, volume bruto, volume liquido, totalizadores, temperatura, pressao.
- Gas linear: tag do ponto, periodo, volume bruto corrigido, volume bruto, pressao estatica, pressao atmosferica, pressao base, temperatura.
- Gas diferencial: tag, periodo, volume, temperatura, pressao, cromatografia.
- BSW em linha: tag, data/hora, `% BSW`, `% Maximo BSW`, boletim de analise, arquivo recebido, data de carga.
- Falha de medicao: codigo da falha, sequencia, tipo de notificacao, tipo de falha, instalacao, datas de ocorrencia/deteccao/retorno, previsao de retorno, tag do ponto e elemento de medicao.

Uso recomendado:

- Criar camada `painel_anp_exports`.
- Validar cobertura diaria por familia fiscal.
- Cruzar volume ANP x XML x CV.
- Trazer falhas para modulo de pendencias/alertas.
- Alimentar status de obrigacoes regulatorias.

### 3. XML fiscal e XML tecnico

Familias fiscais observadas:

- `001_*`: raiz `a001`, oleo linear.
- `002_*`: raiz `a002`, gas linear.
- `003_*`: raiz `a003`, gas diferencial.
- `039_*`: raiz `a039`, falha de medicao/NFSM.

Estrutura fiscal relevante:

- `a001`: configuracao CV, numero de serie do computador de vazao, coleta, temperatura, pressoes, software, elemento primario, meter factors, K factors.
- `a002`: configuracao gas linear, cromatografia, densidade relativa, AGA, pressoes e temperatura.
- `a003`: gas diferencial, cromatografia, limites de pressao, instrumentos e alarmes.
- `a039`: falha, acao, metodologia, responsavel, volumes declarado/registrado.

Outros XMLs encontrados:

- `Parameters.xml`: 50 arquivos, raiz `tags`, milhares de tags por computador de vazao.
- `Security.xml`: 50 arquivos, raiz `security`.
- XMLs de certificados de calibracao e placa de orificio.
- XMLs `Workbook` exportados por ferramentas externas.

Uso recomendado:

- Criar parser fiscal especifico para 001/002/003/039.
- Criar parser tecnico para `Parameters.xml`, extraindo parametro, valor, unidade, data e flow computer.
- Manter XMLs de certificado como evidencia documental inicialmente; parser estruturado pode vir depois.

### 4. CSVs historicos / PI / Performance Monitoring

Arquivos principais:

- `BAC_Fiscal Metering Daily Monitoring.csv`
- `Metering Bacalhau.csv`
- `BAC_SUB Prod Flowline P2 - PE2 only.csv`
- `BAC_SUB Prod Flowline P4 - PW104 only.csv`
- `BAC_SUB Prod Flowline P5 - PE4 only.csv`
- `BAC_SUB Gas Injection.csv`
- `BAC_SUB Prod Well.csv`
- duplicatas em `dashboard-anp-radar/MODELOS`.

Formato observado:

- Colunas logicas: `Fonte de dados`, `Tempo`, `Valor`.
- Os caminhos de fonte seguem estrutura hierarquica, por exemplo `\\AFBRA\BRA\Bacalhau\System 20\All Equipment\20FT2303GSV|Gsvfr`.
- Ha mistura de separadores/locale: cabecalho com virgula e linhas de dados com ponto e virgula; valores usam virgula decimal.

Uso recomendado:

- Criar parser streaming para CSV grande.
- Normalizar `Fonte de dados` em: sistema, equipamento/tag, variavel, unidade/contexto.
- Criar tabela de series temporais para dados monofasicos, flowline, riser, injecao e pocos.
- Nao carregar tudo em memoria; usar chunks.
- Resolver duplicatas raiz vs `MODELOS` por hash.

### 5. Excel de cadastro, calibracao, IHM e controle

Arquivos de alto valor:

- `Relação de CV por sistema de medição.xlsx`
- `Calibration Control - Primários.xlsx`
- `BAC - Calibration Plan - 15-04-2025.xlsx`
- `Validacao de Corrida de Calibracao *.xlsx`
- `Daily_Oil_*.xlsx`, `Daily_Gas_*.xlsx`, `Daily_Water_*.xlsx`, `GasBalance_*.xlsx`
- `MPFM_JUN_2026.xlsx`
- checklists de certificados e incerteza.

Informacao util observada:

- Cadastro CV: endereco, FC, tag do CV, numero de serie, firmware, aplicacao, tipo, tag/sistema conectado.
- Master Config Oil/Gas/Water: parametros de configuracao por familia.
- Calibration Plan: aplicacao, servico, tag, classificacao, status, sistema, localizacao, plano de manutencao, SAP code.
- Calibration Control: tag, numero de serie, equipamento, faixa calibrada, certificado, proxima calibracao, periodicidade ANP, status e dias para vencimento.
- Validacao de corrida: run, data, medidor, provador, vazao alvo, vazao media, MF calculado, pressoes e temperaturas.
- IHM reports: relatorios diarios por oleo/gas/agua com periodo, campo, volumes, massa, pressoes, temperaturas e densidades.

Uso recomendado:

- Criar cadastro tecnico de medidores/CVs a partir da relacao de CV.
- Criar modulo de calibracao com validade, periodicidade, certificado e status.
- Criar historico de validacoes de corrida com MF calculado.
- Usar IHM Reports como fonte operacional secundaria para reconciliacao e validacao de volumes.

### 6. Dossie fiscal, operacional e documentos

Pastas principais:

- `02 FISCAL`
- `04 OPERATIONAL` dentro dos pacotes OneDrive.
- `Documentação - Book ANP`.
- `02 - Memorial Descriptive`.

Categorias detectadas:

- Fiscal oleo: 127 documentos, 43,38 MB.
- Flowline: 80 documentos, 25,46 MB.
- Flare: 94 documentos, 65,37 MB.
- Fuel gas/IGG: 179 documentos, 51,44 MB.
- Separador de teste: 72 documentos, 33,27 MB.
- Offloading: 129 documentos, 58,88 MB.
- Incerteza: 149 documentos, 46,77 MB.
- Certificados/padroes: 381 documentos, 142,19 MB.
- Memorial descritivo: 11 documentos, 302,18 MB.
- Manuais/RTM/Book ANP: 29 documentos, 18,97 MB.

Uso recomendado:

- Primeira fase: indexar metadados, caminho, hash, tag inferida, data, categoria e tipo de evidencia.
- Segunda fase: extrair texto com `pdfplumber`/`pypdf` e classificar por requisito.
- Terceira fase: vincular documento a ponto de medicao, requisito, certificado, incerteza, calibracao ou falha.

### 7. Radar ANP existente

O app `dashboard-anp-radar` ja e uma aplicacao separada com:

- `scripts/build_dashboard_data.py`: pipeline de consolidacao.
- `server/radar-api.mjs`: API Node local.
- `src/data/dashboard-data.json`: contrato consolidado.
- `data/radar-anp.sqlite`: banco gerado.
- `docs/`: regras, fluxo de rastreabilidade, dados necessarios e correlacionador evento/evidencia.

SQLite do Radar:

- `alerts`: 15 linhas.
- `calendar_pendencies`: 71 linhas.
- `change_proposals`: 57 linhas.
- `comparisons`: 24 linhas.
- `event_evidence_events`: 57 linhas.
- `files`: 14 linhas.
- `limit_monitors`: 12 linhas.
- `operational_calendar`: 61 linhas.
- `regulatory_requirements`: 42 linhas.
- `uncertainty_monitor`: 24 linhas.

Uso recomendado:

- Continuar usando como nucleo do modulo Painel do Operador.
- Nao misturar a UI React do Radar com o MPFM.
- Migrar gradualmente parsers e entidades para servicos Python do backend principal.
- Usar `dashboard-data.json` e `radar-anp.sqlite` como ponte temporaria, como ja iniciado no staging.

## Dados imediatamente aproveitaveis na aplicacao

### Para modulo monofasico fiscal

- XML 001/002/003.
- Exports `Óleo Linear`, `Gás Linear`, `Gás Diferencial`.
- CSVs historicos por tag.
- Daily TXT dos CVs.
- IHM Reports.

Entidades sugeridas:

- `measurement_point`
- `flow_computer`
- `fiscal_meter_daily`
- `fiscal_meter_hourly`
- `anp_export_row`
- `xml_fiscal_row`
- `raw_cv_daily`
- `raw_cv_hourly`

### Para modulo de falhas e pendencias

- `Falha de Medição.xlsx`.
- XML 039.
- `AlarmsAndEvents_Daily` e `AlarmsAndEvents_Hourly`.
- `change_proposals` do Radar.
- `calendar_pendencies` do Radar.

Entidades sugeridas:

- `measurement_failure`
- `alarm_event`
- `parameter_change`
- `pendency`
- `corrective_action`

### Para modulo de calibracao e incerteza

- `Calibration Control - Primários.xlsx`.
- `BAC - Calibration Plan - 15-04-2025.xlsx`.
- Validacoes de corrida.
- Checklists de certificados.
- PDFs/XMLs de certificados.
- Documentos de incerteza `BAC-UCG-*`.

Entidades sugeridas:

- `calibration_plan`
- `calibration_certificate`
- `calibration_run_validation`
- `uncertainty_report`
- `certificate_evidence`

### Para modulo documental e regulatorio

- Book ANP.
- RTM, manuais XML 001/002/003/004.
- Memorial descritivo.
- Matriz SGM1 do Radar.
- PDFs de evidencias.

Entidades sugeridas:

- `regulatory_requirement`
- `evidence_document`
- `document_text_index`
- `requirement_evidence_link`

## Riscos e cuidados tecnicos

- Caminhos antigos ainda aparecem em dados gerados pelo Radar, principalmente `C:\Users\mauri\OneDrive\...`; a aplicacao precisa manter normalizacao para `C:\MPFM\NOVO\Painel_Operador`.
- Ha muitos duplicados por nome/tamanho: 3.276 arquivos aparecem em grupos repetidos no indice leve. Antes de ingerir documentos grandes, usar hash de conteudo ou cache incremental.
- Nao processar `.git`, `node_modules`, `dist`, `release`, `.playwright-mcp`, `__pycache__`, zips de transporte e caches.
- CSVs grandes devem ser processados em streaming.
- Datas misturam portugues/ingles e formatos `DD/MM/YY`, `YYYY-MM-DD`, `Jun-2026`.
- Valores usam virgula decimal em varios arquivos ANP/PI/XML.
- PDFs e DOCX devem entrar primeiro como evidencia com metadados; extracao textual completa pode ser fase 2.
- Arquivos `Security.xml` podem conter usuarios/perfis; tratar como dado sensivel.

## Prioridade recomendada

1. Criar um indice de fontes do Painel do Operador com regras de exclusao e hash. Implementado no backend em `painel_operador_file_index`.
2. Implementar parser fiscal 001/002/003/039 e parser dos exports ANP.
3. Implementar parser TXT dos CVs para `Run_Daily`, `Run_24Hours`, `Run_Hourly` e `AlarmsAndEvents`.
4. Implementar parser de CSV PI/performance em streaming.
5. Implementar cadastro tecnico a partir de `Relação de CV por sistema de medição.xlsx`.
6. Implementar calibracao/incerteza a partir de planilhas de controle e validacao.
7. Indexar documentos PDF/DOCX como evidencias, depois extrair texto e vincular a requisitos.

## Indice de fontes implementado

Endpoints adicionados:

- `POST /api/painel-operador/file-index/scan`: varre a pasta do Painel do Operador e atualiza o indice persistente.
- `GET /api/painel-operador/file-index-summary`: mostra a ultima varredura e distribuicao por categoria.
- `GET /api/painel-operador/file-index`: consulta arquivos indexados com filtros.

Tabelas:

- `painel_operador_file_index_runs`
- `painel_operador_file_index`

Campos principais do indice:

- caminho relativo e completo;
- extensao, tamanho, data de modificacao;
- identificador estavel e hash SHA-1 de conteudo quando a varredura completa estiver habilitada;
- chave de duplicidade;
- categoria e tipo documental;
- grupo de fonte;
- data/tag/familia inferidas;
- prioridade de parser;
- flag de duplicidade;
- flag de ignorado e motivo.

Validacao real executada em modo leve/metadados:

- Execucao `painel_operador_file_index_runs.id = 3`, iniciada em `2026-07-03T11:49:31` e finalizada em `2026-07-03T11:49:38`.
- Pasta raiz: `C:\MPFM\NOVO\Painel_Operador`.
- 6.485 arquivos encontrados, 6.481 indexados diretamente e 4 ignorados por baixo valor operacional.
- Volume catalogado: 3.803.892.709 bytes.
- 3.276 arquivos marcados como duplicados por chave leve baseada em nome/tamanho.
- A varredura com hash completo foi testada, mas excedeu 300 segundos no fluxo HTTP sincronico; deve virar job assíncrono/incremental antes de uso rotineiro.

Distribuicao principal da execucao:

- `daily_report`: 4.141 arquivos.
- `fiscal_document`: 1.282 arquivos.
- `calibration_certificate`: 226 arquivos.
- `evidence_document`: 178 arquivos.
- `uncertainty_document`: 149 arquivos.
- `technical_workbook`: 133 arquivos.
- `pi_timeseries`: 59 arquivos.
- `radar_app`: 38 arquivos.
- `archive`: 24 arquivos.
- `technical_xml`: 22 arquivos.
- `anp_operator_export`: 5 arquivos.
- `anp_xml`: 1 arquivo.

Consultas validadas:

- `GET /api/painel-operador/file-index?category=daily_report&document_kind=cv_run_daily_txt&limit=3`: 102 arquivos `Run_Daily`, com tags inferidas como `20FT2303` e `20FT2353`.
- `GET /api/painel-operador/file-index?category=anp_operator_export&limit=10`: 5 exports ANP localizados (`Óleo Linear.xlsx`, `Gás Linear.xlsx`, `Gás Diferencial.xlsx`, `BSW em Linha.xlsx`, `Falha de Medição.xlsx`) com familias `a001`, `a002`, `a003`, `a040`, `a039`.
- `GET /api/painel-operador/file-index?category=pi_timeseries&limit=3`: 59 CSVs de performance/PI localizados.
- `GET /api/painel-operador/file-index?is_duplicate=1&limit=3`: 3.276 entradas duplicadas por chave leve.

## Parser inicial de exports ANP implementado

Os 5 arquivos ANP de maior prioridade foram importados para uma tabela operacional propria, sem misturar com as telas atuais:

- `POST /api/painel-operador/anp-exports/import`: importa os exports para staging normalizado.
- `GET /api/painel-operador/anp-exports-summary`: resume a ultima importacao.
- `GET /api/painel-operador/anp-exports`: lista registros com filtros por familia, tag, tipo, arquivo, tipo de falha e data.

Tabelas:

- `painel_operador_anp_export_runs`
- `painel_operador_anp_export_rows`

Primeira importacao real:

- Execucao `painel_operador_anp_export_runs.id = 1`, finalizada em `2026-07-03T12:43:33`.
- 5 arquivos importados.
- 3.876 linhas normalizadas.
- `a001 / linear_oil`: 953 linhas.
- `a002 / linear_gas`: 712 linhas.
- `a003 / differential_gas`: 1.170 linhas.
- `a039 / measurement_failure`: 89 linhas.
- `a040 / inline_bsw`: 952 linhas.

Campos normalizados:

- arquivo, caminho, aba, linha original;
- familia, nome do export e tipo de registro;
- instalacao, codigo, tag, elemento e numero de serie;
- datas de referencia, periodo, ocorrencia, deteccao, retorno, coleta e carga;
- volume corrigido/bruto/liquido, BSW, pressao, temperatura;
- codigo/tipo de falha, tipo de notificacao e arquivo recebido;
- payload bruto da linha para auditoria.

Consultas validadas:

- `GET /api/painel-operador/anp-exports?family=a001&tag=20FT2303&limit=3`: 238 registros.
- `GET /api/painel-operador/anp-exports?record_kind=inline_bsw&tag=20FT2303&limit=3`: 237 registros.
- `GET /api/painel-operador/anp-exports?record_kind=measurement_failure&limit=3`: 89 registros.
