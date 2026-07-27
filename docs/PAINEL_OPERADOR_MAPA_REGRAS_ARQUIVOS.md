# Painel do Operador - Mapa de regras, telas e fontes

Data da leitura: 2026-07-03

Raiz analisada: `C:\MPFM\NOVO\Painel_Operador\dashboard-anp-radar`

Este documento registra onde ficam as regras do Radar ANP/Painel do Operador e como elas devem ser aproveitadas na integração modular com o MPFM Manager.

## Arquivos principais localizados

| Arquivo | Papel real | Tamanho / linhas | Uso recomendado no MPFM |
|---|---|---:|---|
| `scripts/build_dashboard_data.py` | Motor de regras. Lê fontes configuradas, processa XML/ZIP, CV TXT, exports ANP, BSW, falhas, matriz SGM, eventos, evidências, limites, incerteza e gera JSON/SQLite. | 119.794 bytes / 3.015 linhas | Usar como referência de regra e migrar por blocos para serviços Python próprios do MPFM. Não chamar tudo como caixa-preta dentro de tela. |
| `src/App.jsx` | Interface React do Radar: Operação, Trilha E2E, Calendário, Prazos, Propostas, Configuração, Pergunte ao Radar, Dossiê, gráficos e tabelas. | 91.031 bytes / 2.210 linhas | Usar como mapa funcional. Não embutir a tela React inteira no MPFM; reproduzir apenas funcionalidades úteis em módulos separados. |
| `server/radar-api.mjs` | API local Node sem depender do Vite: configuração, dados, rebuild, decisões de propostas/pendências, IA local/LLM e estáticos. | 35.708 bytes / 928 linhas | Reaproveitar comportamento de endpoints no backend FastAPI quando fizer sentido. Evitar depender de segundo servidor em produção. |
| `config/data-sources.json` | Inventário de 14 grupos de fontes, todos normalizados para `C:\MPFM\NOVO\Painel_Operador`. | 4.560 bytes | Base para tela de configuração futura e para classificação do índice de fontes. |
| `src/data/dashboard-data.json` | Snapshot gerado que alimenta telas do Radar. | 1.448.441 bytes | Já usado pelo staging inicial (`sync`). Deve continuar como contrato temporário, não como fonte única permanente. |
| `data/radar-anp.sqlite` | Banco SQLite local gerado pelo motor de regras. | 929.792 bytes | Fonte de auditoria e comparação. Já exposto em resumo; pode alimentar consultas específicas. |
| `src/styles.css` | Visual/layout do Radar React. | 52.911 bytes / 3.129 linhas | Referência visual apenas. O MPFM deve preservar seu próprio design system. |
| `config/ai-settings.local.json` | Configuração local sensível de IA/modelos/chaves/permissões. | 943 bytes | Não versionar, não exibir chaves. Pode inspirar configuração de permissões e auditoria no MPFM. |
| `tests/test_build_dashboard_data.py` | Testes das regras centrais: número brasileiro, datas, eventos, evidência, calendário e governança. | 8.347 bytes / 186 linhas | Migrar testes conforme as regras forem portadas para serviços MPFM. |

## Documentação localizada

| Documento | Conteúdo essencial | Impacto na integração |
|---|---|---|
| `docs/REGRAS_RADAR.md` | Regras de envio/recebimento ANP, raw/XML/ANP, eventos sem evidência, limites/PAM, calibração, incerteza, físico-química, falhas e dossiê. | Deve virar backlog de regras auditáveis no MPFM. |
| `docs/FLUXO_RASTREABILIDADE.md` | Princípio bronze/silver/gold/evidência; fluxo raw -> XML -> ANP; estrutura de registro de auditoria. | Confirma que devemos persistir origem, camada, cálculo e recomendação antes de consumir em módulos monofásicos. |
| `docs/CORRELACIONADOR_EVENTO_EVIDENCIA.md` | Regras de classificação de eventos, pontuação de evidência, extração textual e estados `confirmed/supporting/candidate/missing`. | Próximo bloco forte para portar: evidência documental vinculada a eventos. |
| `docs/DADOS_NECESSARIOS.md` | Fontes obrigatórias e desejáveis: dailyReports, xmlSent, anpPanel, cvRaw, alarmsEvents, cadastro, mpfm, physchem, calibration, uncertainty, equipmentDocs etc. | Já suporta o índice de fontes; ajuda a priorizar parsers restantes. |
| `docs/ai-operational-context.md` | Manifesto usado pela IA: fontes, dados gerados, SQLite, telas, permissões e regras de resposta. | Pode alimentar o Assistente IA do MPFM, com escopo e permissões explícitos. |
| `docs/PLANO_CONTINGENCIA_SEM_VITE.md` | Arquitetura sem Vite: `server/radar-api.mjs`, `esbuild`, endpoints `/api/*`, dist estático. | Confirma que não devemos depender do Vite; nossa integração FastAPI é alinhada à rota C/Python server. |
| `docs/ANALISE_MATERIAL_RECEBIDO.md` | Volumetria, fontes fiscais reais, matriz SGM1 e regras novas recomendadas. | Boa base para priorização de documentos fiscais, calibração, incerteza e PAM. |
| `docs/TEMPLATE_INGESTAO.md` | Abas de contingência manual e regra de revisão humana. | Útil para futura tela de ingestão manual estruturada. |

## Dados gerados pelo Radar

O `dashboard-data.json` atual contém os seguintes blocos:

- `meta`, `config`, `kpis`, `families`;
- `files`, `closing`, `comparisons`, `latestPoints`;
- `limitMonitors`, `uncertaintyMonitor`;
- `analytical`, `measurementModels`, `operatorPanelHealth`;
- `ai`, `regulatoryMatrix`, `eventEvidenceRadar`;
- `changeProposals`, `operationalCalendar`;
- `bsw`, `failures`, `mpfm`, `alerts`, `database`.

Os blocos que já foram trazidos para o MPFM em staging:

- `files` -> `painel_operador_sources`;
- `latestPoints` -> `painel_operador_measurement_points`;
- `comparisons` -> `painel_operador_comparisons`;
- `eventEvidenceRadar` e `regulatoryMatrix` -> `painel_operador_evidence`;
- `alerts` e `changeProposals` -> `painel_operador_alerts`.
- `changeProposals` -> `painel_operador_proposals`.
- `operationalCalendar.days` -> `painel_operador_calendar_days`.
- `operationalCalendar.days[].pendingItems` -> `painel_operador_calendar_pendencies`.

Os 5 exports ANP também já foram normalizados em tabela própria:

- `Óleo Linear.xlsx` -> `a001 / linear_oil`;
- `Gás Linear.xlsx` -> `a002 / linear_gas`;
- `Gás Diferencial.xlsx` -> `a003 / differential_gas`;
- `Falha de Medição.xlsx` -> `a039 / measurement_failure`;
- `BSW em Linha.xlsx` -> `a040 / inline_bsw`.

## SQLite do Radar

Tabelas geradas pelo Radar local:

- `metadata`: geração, datas, raiz e caminhos.
- `kpis`: indicadores principais.
- `sources`: fontes configuradas.
- `files`: XMLs e arquivos identificados.
- `comparisons`: conciliação raw -> XML -> ANP por ponto/data.
- `closing`: fechamento diário.
- `alerts`: alertas operacionais/regulatórios.
- `limit_monitors`: limites, PAM/faixa e status por ponto.
- `uncertainty_monitor`: cobertura de incerteza.
- `event_evidence_events`: eventos de parâmetro e melhor evidência documental.
- `regulatory_requirements`: requisitos da matriz SGM.
- `change_proposals`: propostas pendentes/autorizadas/rejeitadas/adiadas.
- `operational_calendar`: calendário diário e status.
- `calendar_pendencies`: pendências por dia.

## Regras centrais encontradas em `build_dashboard_data.py`

### Ingestão e normalização

- `load_config`, `configured_paths`, `iter_source_files`, `find_first_file`: leem `data-sources.json`.
- `as_number`, `fmt_date`, `read_export`: normalizam números, datas e planilhas.
- `parse_xml_bytes`, `parse_measurement_xmls`: extraem XMLs 001/002/003/004 de XML e ZIP.
- `parse_cv_daily`: extrai raw CV `Run_Daily`.
- `parse_anp_exports`, `parse_bsw`, `parse_failures`, `parse_points`: extraem dados do Painel ANP e cadastro.
- `parse_measurement_models`: resume CSVs/PI/performance.

### Regras e alertas

- `compare_layers`: compara raw x XML x ANP.
- `build_daily_closing`: fechamento diário.
- `build_alerts`: alertas consolidados.
- `build_limit_monitors`: limites, PAM e envelopes.
- `build_uncertainty_monitor`: cobertura de incerteza.
- `build_operational_calendar`: calendário e pendências.
- `build_change_proposals`: propostas auditáveis.

### Evidência documental

- `parse_alarm_event_txts`: lê `AlarmsAndEvents`.
- `classify_parameter_event`: classifica mudança de parâmetro.
- `index_evidence_files`: indexa documentos candidatos.
- `extract_evidence_text`: extrai texto de PDF/XLSX/DOCX/ZIP/TXT/XML/CSV/HTML.
- `score_evidence_match`: pontua tipo, tag e data.
- `evaluate_content_evidence`: confirma conteúdo por parâmetro/valor.
- `build_event_evidence_radar`: monta radar evento -> evidência.

### Persistência

- `write_sqlite_database`: grava o SQLite local.
- `main`: orquestra tudo e grava `dashboard-data.json` + `radar-anp.sqlite`.

## APIs do Radar Node encontradas

No `server/radar-api.mjs`, as rotas relevantes são:

- `GET /api/config`;
- `POST /api/config`;
- `GET /api/data`;
- `POST /api/proposals/decision`;
- `POST /api/pendencies/decision`;
- `GET /api/database-summary`;
- `GET /api/ai-config`;
- `POST /api/ai-config`;
- `POST /api/ask`;
- `POST /api/rebuild`.

Pontos de segurança já existentes:

- validação de origem local;
- limite de payload;
- validação de caminhos dentro da raiz;
- proteção contra segmentos inseguros;
- rate limit para perguntas da IA;
- mascaramento de chaves no retorno de configuração;
- log JSONL de perguntas/decisões.

## Telas do Radar encontradas em `src/App.jsx`

As telas principais são:

- `operacao`: KPIs, saúde do Painel do Operador, tabela raw/XML/ANP, alertas, gráfico, painéis analíticos e dossiê.
- `trilha`: trilha E2E por dia.
- `calendario`: dias carregados/não carregados e baixa de pendências.
- `prazos`: falhas e obrigações.
- `propostas`: fila de propostas auditáveis com autorizar/rejeitar/adiar.
- `config`: fontes, rebuild, banco local e IA.
- `Pergunte ao Radar`: resposta local/LLM auditável.
- `Dossiê do ponto`: contexto por tag.

No MPFM, a tela `#painel-operador` recém-criada deve ser a porta de entrada, mas sem copiar a experiência inteira do React Radar.

## O que já está aplicado no MPFM Manager

- Catálogo de arquivos da pasta `Painel_Operador`.
- Importação dos 5 exports ANP principais.
- Staging dos blocos consolidados do `dashboard-data.json`.
- Tela frontend `#painel-operador` com:
  - visão geral;
  - ingestão/configuração de caminhos;
  - fontes;
  - exports ANP;
  - dados medidos;
  - apuração diária por dia de produção;
  - comparação ANP x staging;
  - calendário operacional e pendências;
  - propostas auditáveis;
  - staging.

## Próximas integrações recomendadas

1. **Normalização de comparação fiscal x MPFM**
   - Evoluir a aba `Dados Medidos`/apuração diária de leitura agregada para comparação auditável por tag/dia.
   - Criar regra explícita de unidade/densidade antes de calcular delta entre volume fiscal/ANP em m3 e MPFM em t.
   - Separar status de dado ausente, unidade incompatível, valor divergente e valor compatível.

2. **Decisão auditável de propostas**
   - Implementar autorizar/rejeitar/adiar no backend FastAPI.
   - Persistir decisões separadas do snapshot gerado, seguindo o padrão `proposal-decisions.json` do Radar.

3. **Portar correlacionador evento -> evidência**
   - Primeiro como leitura/staging, não como alteração de cadastro.
   - Aproveitar `event_evidence_events` e a lógica de pontuação.

4. **Portar limites/PAM e incerteza**
   - Persistir `limitMonitors` e `uncertaintyMonitor` em tabelas específicas.
   - Cruzar depois com módulos monofásicos e monitoramento MPFM.

5. **Assistente IA com contexto operacional**
   - Usar `ai-operational-context.md` como manifesto do Assistente IA, mas mantendo permissões explícitas e sem expor chaves.

## Cuidados

- `config/ai-settings.local.json` é sensível; não exibir chaves nem versionar.
- `src/data/dashboard-data.json` é snapshot gerado; não editar manualmente.
- `radar-anp.sqlite` é produto do processamento; usar como leitura/auditoria.
- `build_dashboard_data.py` deve ser portado por módulos pequenos, com testes, em vez de ser chamado como caixa-preta dentro da UI.
- As telas do Radar servem como referência funcional, não como componente a ser embutido no MPFM.
