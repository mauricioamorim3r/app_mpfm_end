# Painel do Operador como modulo separado

## Decisao

O Painel do Operador deve entrar no projeto como um modulo operacional separado, sem misturar as telas atuais do MPFM com as telas do Radar ANP. A aplicacao copiada em `Painel_Operador/dashboard-anp-radar` continua sendo o primeiro nucleo desse modulo.

O papel inicial desse modulo e localizar, analisar e consolidar informacoes espalhadas em pastas, XMLs fiscais, planilhas do Painel ANP, CSVs, PDFs, certificados, relatorios diarios, alarmes e matrizes regulatorias. O MPFM e os futuros modulos monofasicos devem consumir somente dados ja extraidos, normalizados e armazenados.

## Fronteiras

- `Painel_Operador/dashboard-anp-radar`: modulo de varredura, analise documental, rastreabilidade ANP e formacao de base de evidencias.
- `server.py`, `routes/`, `services/`, `repositories/`: aplicacao MPFM atual, com paginas e APIs proprias.
- `data/`: base operacional do MPFM atual.
- Base futura de monofasicos: destino dos dados fiscais e operacionais consolidados que forem promovidos pelo modulo Painel do Operador.

## Regra de integracao

O MPFM nao deve depender diretamente das telas React do Radar ANP. A integracao deve acontecer por contratos de dados:

1. O Painel do Operador varre fontes externas e gera dados consolidados.
2. Os dados consolidados sao validados e gravados em uma base propria ou em tabelas de staging.
3. Os sistemas MPFM/monofasicos leem esses dados por APIs ou consultas normalizadas.
4. Somente depois disso criamos telas especificas no MPFM para usar esses dados.

## Camadas propostas

### 1. Coleta e evidencia

Responsavel por encontrar arquivos, registrar origem, hash, data, tipo documental, periodo de competencia e relacao com requisitos ANP/SGM.

Entradas principais:

- XMLs fiscais 001/002/003/004.
- Exports do Painel ANP.
- Daily reports.
- TXT/CSV de computadores de vazao.
- Certificados, calibracoes, incerteza, PVT, cromatografia, BSW e documentos regulatorios.

### 2. Normalizacao

Responsavel por transformar os arquivos encontrados em entidades estaveis:

- instalacao;
- ponto de medicao;
- medidor;
- fluido;
- periodo de medicao;
- volume/massa/energia;
- evento/falha;
- requisito regulatorio;
- evidencia documental.

### 3. Staging fiscal-operacional

Responsavel por armazenar os dados extraidos antes de eles virarem informacao de negocio nos sistemas MPFM/monofasicos. Essa camada deve preservar rastreabilidade e permitir reprocessamento.

### 4. Consumo pelos sistemas

Responsavel por entregar informacao ja confiavel para:

- reconciliacao;
- monitoramento monofasico;
- comparacao MPFM x referencia fiscal;
- prazos e obrigacoes;
- relatorios mensais;
- auditoria e memoria de calculo.

## Proximos passos tecnicos

1. Manter o Radar ANP executavel como modulo separado dentro de `Painel_Operador/dashboard-anp-radar`.
2. Remover dependencia de caminhos antigos e usar `C:\MPFM\NOVO\Painel_Operador` como raiz local.
3. Criar um contrato de saida inicial baseado em `src/data/dashboard-data.json` e `data/radar-anp.sqlite`.
4. Mapear quais tabelas/entidades desse contrato devem alimentar os modulos monofasicos.
5. Portar gradualmente os parsers e o pipeline de rebuild para servicos Python do projeto principal, mantendo a interface do modulo separada.

## Contrato inicial observado

O arquivo `Painel_Operador/dashboard-anp-radar/src/data/dashboard-data.json` ja possui blocos que podem virar contrato de integracao:

- `families`: familias fiscais XML 001/002/003/004.
- `files`: fontes localizadas e classificadas.
- `comparisons`: comparacoes entre XML, exports ANP e dados consolidados.
- `latestPoints`: ultimos pontos de medicao observados.
- `limitMonitors` e `uncertaintyMonitor`: monitoramento de limites e incerteza.
- `operatorPanelHealth`: cobertura e saude dos exports do Painel ANP.
- `regulatoryMatrix`: requisitos e matriz regulatoria.
- `eventEvidenceRadar`: relacao evento/evidencia.
- `changeProposals`: propostas de ajustes ou pendencias detectadas.
- `operationalCalendar`: calendario operacional e vencimentos.
- `bsw`, `failures`, `mpfm` e `alerts`: blocos operacionais que podem alimentar os modulos monofasicos.
- `database`: resumo do banco SQLite gerado pelo modulo.

## APIs de staging criadas

As primeiras APIs read-only do modulo foram expostas no backend principal, sem criar tela nova e sem importar dados para a base MPFM:

- `GET /api/painel-operador/status`: verifica arquivos consolidados, configuracao e resumo do SQLite do Radar ANP.
- `GET /api/painel-operador/contract`: lista os blocos disponiveis no `dashboard-data.json`, com tipo, contagem e chaves de amostra.
- `GET /api/painel-operador/data?blocks=meta,kpis,alerts&max_list_items=200`: retorna blocos selecionados do contrato, com limite para listas grandes.
- `GET /api/painel-operador/database-summary`: lista tabelas e contagens do SQLite `radar-anp.sqlite`.
- `GET /api/painel-operador/data-sources?validate=true`: lista as fontes configuraveis e valida caminhos/pastas/subpastas.
- `POST /api/painel-operador/data-sources/validate`: executa validacao das fontes configuradas.
- `POST /api/painel-operador/data-sources/{source_id}`: salva caminhos, tipo e recursividade de uma fonte no `config/data-sources.json`.
- `POST /api/painel-operador/sync`: sincroniza o contrato atual para tabelas de staging no banco MPFM.
- `GET /api/painel-operador/staging-summary`: mostra a ultima sincronizacao e as contagens persistidas.
- `GET /api/painel-operador/staging/{tipo}`: consulta registros de staging com filtros e paginacao.
- `POST /api/painel-operador/file-index/scan?hash_files=false`: cataloga os arquivos da pasta `Painel_Operador` em modo leve/metadados.
- `GET /api/painel-operador/file-index-summary`: mostra a ultima varredura do catalogo de arquivos.
- `GET /api/painel-operador/file-index`: consulta o catalogo de arquivos por categoria, tipo documental, tag, familia, data e duplicidade.
- `POST /api/painel-operador/anp-exports/import`: importa os exports ANP principais para staging normalizado.
- `GET /api/painel-operador/anp-exports-summary`: mostra a ultima importacao dos exports ANP.
- `GET /api/painel-operador/anp-exports`: consulta linhas dos exports ANP com filtros por familia, tag, tipo, arquivo, falha e janela de data.
- `GET /api/painel-operador/anp-comparison`: cruza exports ANP normalizados com o staging `comparisons` por data, familia e tag, classificando linhas como `matched`, `value_mismatch`, `anp_only`, `staging_only` ou `not_comparable`.
- `GET /api/painel-operador/production-days`: consolida por dia de producao arquivos catalogados, Fiscal/Radar, export ANP, MPFM diario e pendencias do calendario.
- `GET /api/painel-operador/measured-data`: agrega dados medidos por dia e detalhe, separando `fiscal_radar`, `anp_export` e `mpfm_daily` com unidades explicitas.
- `GET /api/painel-operador/staging/calendar`: consulta dias do calendario operacional do Radar, sem misturar com `deadline_items`.
- `GET /api/painel-operador/staging/pendencies`: consulta pendencias do calendario operacional, com status, severidade, acao recomendada e payload original.
- `GET /api/painel-operador/staging/proposals`: consulta propostas auditaveis do Radar por status, risco, dominio, alvo, evidencia, confianca e busca textual.

Essas APIs sao a fronteira inicial entre o modulo Painel do Operador e os futuros consumidores MPFM/monofasicos.

## Tabelas de staging persistente

A sincronizacao cria um snapshot atual idempotente nas tabelas abaixo, mantendo historico das execucoes em `painel_operador_sync_runs`:

- `painel_operador_sources`: fontes e arquivos classificados, com caminho original, caminho local normalizado, existencia, tamanho e hash.
- `painel_operador_measurement_points`: pontos fiscais/operacionais observados no contrato consolidado.
- `painel_operador_comparisons`: comparacoes raw/XML/Painel ANP.
- `painel_operador_evidence`: eventos, evidencias e requisitos regulatorios.
- `painel_operador_alerts`: alertas e propostas de ajuste.
- `painel_operador_proposals`: propostas auditaveis do Radar, com status, risco, evidencia, valor atual/proposto, fonte e trilha.
- `painel_operador_calendar_days`: dias operacionais do Radar, com estado de carga, familias XML, pendencias e contadores.
- `painel_operador_calendar_pendencies`: pendencias do calendario, com status, severidade, tipo, acao recomendada e dados de baixa quando houver.

Essas tabelas ainda nao alimentam telas nem calculos MPFM. Elas existem para formar a base confiavel que depois podera ser consumida pelos modulos monofasicos.

O catalogo de fontes usa tabelas separadas para manter a auditoria dos arquivos sem misturar com o staging de dados consolidados:

- `painel_operador_file_index_runs`: historico das varreduras do catalogo.
- `painel_operador_file_index`: arquivos localizados, classificacao, prioridade de parser, tag/familia/data inferidas e duplicidade.
- `painel_operador_anp_export_runs`: historico das importacoes dos exports ANP.
- `painel_operador_anp_export_rows`: linhas normalizadas dos exports ANP, com metadados comuns e payload bruto preservado.

Primeira sincronizacao validada em `2026-07-03T11:08:03`:

- `painel_operador_sources`: 14 registros.
- `painel_operador_measurement_points`: 12 registros.
- `painel_operador_comparisons`: 24 registros.
- `painel_operador_evidence`: 99 registros.
- `painel_operador_alerts`: 72 registros.

## Consultas de auditoria

Tipos aceitos em `GET /api/painel-operador/staging/{tipo}`:

- `sources`
- `points`
- `comparisons`
- `evidence`
- `alerts`

Filtros comuns:

- `q`: busca textual.
- `date_from` e `date_to`: janela por data do tipo consultado.
- `family`, `tag`, `fluid`, `status`, `severity`, `kind`, `area`, `target_id`, `requirement_id`, `meter_type`, `active`, `file_exists`.
- `limit` e `offset`: paginacao.
- `include_payload=true`: inclui o JSON original normalizado no retorno.

Validacoes reais executadas:

- `GET /api/painel-operador/staging/comparisons?family=a001&limit=3`: 8 registros encontrados.
- `GET /api/painel-operador/staging/alerts?kind=proposal&status=pending_authorization&limit=3`: 56 registros encontrados.
- `GET /api/painel-operador/staging/evidence?kind=requirement&limit=3`: 42 registros encontrados.

## Catalogo de fontes validado

Primeira varredura util validada em `2026-07-03T11:49:38`, usando modo leve/metadados:

- 6.485 arquivos encontrados em `C:\MPFM\NOVO\Painel_Operador`.
- 6.481 arquivos classificados.
- 4 arquivos ignorados.
- 3.276 arquivos marcados como duplicados por chave leve de nome/tamanho.
- 3.803.892.709 bytes catalogados.

Principais grupos encontrados:

- `daily_report`: 4.141 arquivos.
- `fiscal_document`: 1.282 arquivos.
- `calibration_certificate`: 226 arquivos.
- `uncertainty_document`: 149 arquivos.
- `technical_workbook`: 133 arquivos.
- `pi_timeseries`: 59 arquivos.
- `anp_operator_export`: 5 arquivos.

Consultas reais validadas:

- `GET /api/painel-operador/file-index?category=daily_report&document_kind=cv_run_daily_txt&limit=3`: 102 arquivos `Run_Daily`.
- `GET /api/painel-operador/file-index?category=anp_operator_export&limit=10`: 5 exports ANP principais.
- `GET /api/painel-operador/file-index?category=pi_timeseries&limit=3`: 59 CSVs PI/performance.
- `GET /api/painel-operador/file-index?is_duplicate=1&limit=3`: 3.276 entradas duplicadas.

Observacao tecnica: a varredura com hash completo de conteudo foi testada, mas excedeu 300 segundos no endpoint sincronico. O caminho recomendado e transformar isso em job assíncrono/incremental antes de usar como rotina.

## Configuracao de fontes de ingestao

A tela `#painel-operador` possui uma aba `Ingestao` para informar e validar os caminhos usados pelo modulo antes de processar dados medidos.

Estado validado em `2026-07-03`:

- 14 fontes configuradas no arquivo `Painel_Operador/dashboard-anp-radar/config/data-sources.json`.
- 1 caminho unico atual: `C:\MPFM\NOVO\Painel_Operador`.
- 6.485 arquivos uteis visiveis nesse caminho, ignorando diretorios tecnicos como `node_modules`, `.git`, `dist` e caches.
- 3,5 GB visiveis nos caminhos atuais.

Cada fonte permite editar caminhos em linhas separadas, marcar busca em subpastas, salvar no JSON de configuracao e validar existencia/volume/extensoes antes de rodar catalogacao ou ingestao pesada.

## Exports ANP importados

Primeira importacao validada em `2026-07-03T12:43:33`:

- 5 arquivos importados.
- 3.876 linhas normalizadas.
- `Óleo Linear.xlsx`: 953 linhas, familia `a001`, tipo `linear_oil`.
- `Gás Linear.xlsx`: 712 linhas, familia `a002`, tipo `linear_gas`.
- `Gás Diferencial.xlsx`: 1.170 linhas, familia `a003`, tipo `differential_gas`.
- `Falha de Medição.xlsx`: 89 linhas, familia `a039`, tipo `measurement_failure`.
- `BSW em Linha.xlsx`: 952 linhas, familia `a040`, tipo `inline_bsw`.

Campos estruturados principais:

- origem: arquivo, caminho, aba e numero da linha;
- classificacao: familia, nome do export e tipo do registro;
- referencia operacional: instalacao, codigo, tag, elemento, numero de serie;
- datas: referencia, inicio/fim de periodo, ocorrencia, deteccao, retorno, coleta e carga;
- medidas: volume corrigido/bruto/liquido, BSW, pressao e temperatura;
- falhas: codigo, tipo de notificacao, tipo de falha e arquivo recebido;
- `payload_json`: linha original normalizada para auditoria.

Consultas reais validadas:

- `GET /api/painel-operador/anp-exports?family=a001&tag=20FT2303&limit=3`: 238 registros de oleo linear para a tag.
- `GET /api/painel-operador/anp-exports?record_kind=inline_bsw&tag=20FT2303&limit=3`: 237 registros de BSW para a tag.
- `GET /api/painel-operador/anp-exports?record_kind=measurement_failure&limit=3`: 89 registros de falha de medicao.

## Comparacao ANP x staging validada

Primeira consulta consolidada validada em `2026-07-03`, usando tolerancia absoluta padrao `0.001`:

- `GET /api/painel-operador/anp-comparison?limit=5`: 3.876 linhas no cruzamento.
- 3.852 linhas classificadas como `anp_only`, porque existem nos exports ANP mas nao no snapshot atual de `painel_operador_comparisons`.
- 24 linhas classificadas como `matched`, correspondendo ao conjunto atual de comparacoes do Radar sincronizado no staging.
- `GET /api/painel-operador/anp-comparison?family=a001&limit=5`: 953 linhas de oleo linear, sendo 945 `anp_only` e 8 `matched`.

A tela `#painel-operador` possui uma aba propria `Comparacao` para consultar esse contrato sem misturar os dados com as telas existentes de `Exports ANP` ou `Staging`.

## Dados medidos operacionais validados

Primeira visao operacional validada em `2026-07-03`, usando tres fontes separadas:

- `fiscal_radar`: valores do staging `painel_operador_comparisons`, com raw/XML/ANP e status do Radar.
- `anp_export`: volumes, BSW, pressao e temperatura dos exports ANP importados.
- `mpfm_daily`: metricas diarias oficiais de `measurements_curated`.

Consultas reais validadas:

- `GET /api/painel-operador/measured-data?date_from=2026-06-01&date_to=2026-06-02&limit=5`: 874 registros no periodo, 2 dias agregados e 3 fontes presentes.
- `GET /api/painel-operador/measured-data?source=mpfm_daily&date_from=2026-06-20&date_to=2026-06-24&limit=5`: 999 registros MPFM diarios e 5 dias agregados.
- `GET /api/painel-operador/measured-data?limit=1`: 65.534 registros medidos disponiveis no contrato atual.

A tela `#painel-operador` possui uma aba propria `Dados Medidos` com filtros por periodo, fonte, familia e tag. Os totais deixam `Fiscal/Radar m3`, `Export ANP m3` e `MPFM HC t` em cards separados para evitar comparacao direta entre volume e massa. Delta fiscal x MPFM deve ser etapa posterior, com normalizacao explicita de unidade/densidade e regra de aceitacao auditavel.

## Apuracao por dia de producao validada

A mesma aba `Dados Medidos` agora possui uma tabela superior de apuracao diaria. Ela cruza, por dia de producao:

- arquivos catalogados no indice (`daily_report`, XML fiscal, exports ANP, certificados, incerteza, PI e evidencias);
- valores Fiscal/Radar do staging `comparisons`;
- volumes, BSW e falhas dos exports ANP;
- metricas oficiais diarias MPFM de `measurements_curated`;
- status e pendencias do calendario operacional.

Validacao real em `2026-07-03T15:19:46`, apos reindexacao leve `painel_operador_file_index_runs.id=5`:

- `GET /api/painel-operador/production-days?date_from=2026-06-01&date_to=2026-06-02&limit=10`: 2 dias retornados, 4.146 arquivos no recorte, 55.150,8132 m3 Fiscal/Radar, 55.150,8132 m3 ANP e 158.351,838 t MPFM HC.
- A tela carregou `335` dias de producao no contrato atual e exibiu 90 dias sem erro de console.

O status do dia e operacional, nao regulatorio: `Completo` exige presenca de Fiscal/Radar, export ANP e MPFM; `Atencao` aparece quando ha pendencia aberta ou alerta fiscal; `Parcial` indica evidencia incompleta. Ainda nao e uma declaracao de fechamento definitivo.

## Calendario operacional validado

Sincronizacao validada em `2026-07-03T14:05:38`, usando o bloco `operationalCalendar` do contrato JSON:

- `painel_operador_calendar_days`: 61 dias operacionais.
- `painel_operador_calendar_pendencies`: 71 pendencias.
- `GET /api/painel-operador/staging/calendar?limit=3`: retorna os dias mais recentes do calendario.
- `GET /api/painel-operador/staging/pendencies?status=open&limit=3`: retorna 70 pendencias abertas.

A tela `#painel-operador` possui uma aba propria `Calendario`, separada da pagina `#prazos` e das tabelas `deadline_items`.

## Propostas auditaveis validadas

Sincronizacao validada em `2026-07-03T14:28:49`, usando o bloco `changeProposals` do contrato JSON:

- `painel_operador_proposals`: 57 propostas auditaveis.
- 56 propostas com status `pending_authorization`.
- 1 proposta com status `deferred`.
- 12 propostas de risco `alto`.
- `GET /api/painel-operador/staging/proposals?status=pending_authorization&severity=alto&limit=3`: 11 propostas pendentes de risco alto.

A tela `#painel-operador` possui uma aba propria `Propostas`, ainda em modo leitura/auditoria. Acoes de autorizar/rejeitar/adiar devem ser implementadas em etapa separada com gravacao explicita de decisao.

## Nao fazer agora

- Nao embutir a tela inteira do Radar ANP dentro da tela atual do MPFM.
- Nao transformar o menu do MPFM em um painel unico com todas as funcoes.
- Nao copiar `node_modules`, `dist`, `release` ou arquivos temporarios para a arquitetura final.
- Nao usar os dados extraidos sem registrar origem, hash e periodo de competencia.
