# Guia de Fontes de Dados do Assistente IA

Status: guia operacional read-only atualizado em 2026-05-20. Acesso visual sem restricao automatica de periodo.

Este arquivo orienta o Assistente IA sobre onde procurar dados quando o usuario pedir analises, detalhes historicos, rastreabilidade ou contexto operacional. A camada implementada fica em `services/ai_tools/tool_registry.py` e injeta contexto no prompt via `/api/ai/ask`.

## Principio de acesso

- O acesso automatico da IA e somente leitura para todos os periodos disponiveis na base.
- A IA pode consultar tabelas SQLite e snapshots internos da aplicacao sem herdar o mes selecionado na tela como restricao.
- Periodo so deve restringir a consulta quando o usuario pedir explicitamente um mes, dia ou intervalo.
- Qualquer acao de escrita, como fechar alarme, atualizar prazo ou registrar atividade, deve virar proposta em `ai_action_requests` e depender de validacao humana na area do Assistente IA.
- Se o usuario aprovar, a IA fica habilitada apenas para alterar o item, alvo e escopo descritos na proposta aprovada; qualquer outro item exige nova proposta e nova aprovacao.
- Quando faltar filtro minimo diferente de periodo, a IA deve perguntar banco, TAG, fonte, status ou granularidade antes de responder.
- Quando uma integracao externa nao existir, a IA deve dizer isso claramente e usar apenas dados importados na aplicacao.

## Mapa rapido por pergunta

| Pedido do usuario | Onde procurar | Ferramenta interna |
| --- | --- | --- |
| Medicoes MPFM por poco, stream, banco, TAG, hora ou dia | `measurements_active`, `measurements_curated`, `measurements_raw` | `measurement_detail`, `production_summary` |
| Pressao, temperatura, densidade, PVT e parametros brutos | `measurements_active`, `measurements_raw`, `pvt_params` | `measurement_detail`, `asset_register` |
| Separador SEP por fase, hora, dia ou arquivo fonte | `measurements_active`, `sep_source_files`, `sep_alignments` | `sep_detail` |
| Alarmes PDF, workbook, abertos, criticos ou recorrentes | `alarm_records` | `alarm_summary`, `open_alarms` |
| Historico de resolucao de alarmes | `alarm_actions`, `alarm_audit_log` | `alarm_resolution_history` |
| Issues de validacao e causa raiz | `validation_issues`, `parsing_events_raw`, `source_files_raw` | `validation_issues`, `validation_issue_details` |
| Prazos ativos, vencidos, concluidos ou evidencias | `deadline_items` | `deadlines`, `deadline_history` |
| Ativos, pocos, tags subsea, bancos, MPFMs e cadastro | `well_catalog_042`, `mpfm_monitoring_daily`, `pvt_params`, `sep_alignments` | `asset_register` |
| Configuracoes e calibracoes MPFM/PVT | `pvt_params`, `recon_campaigns`, `recon_runs` | `asset_register`, `recon_calibration` |
| Relatorios de reconciliacao, desvios e fator K | `recon_runs`, `recon_campaigns` | `recon_calibration` |
| Arquivos importados, runs, origem e hash | `processing_runs`, `files_imported`, `source_files_raw`, `sep_source_files` | `import_traceability` |
| Radar ANP end-to-end, template de ingestao e governanca | `painel_operador_*`, `docs/RADAR_ANP_PLANO_MESTRE.md`, `docs/RADAR_ANP_TEMPLATE_GERAL_INGESTAO.md`, `templates/Radar_ANP_Template_Geral_Ingestao.xlsx` | `painel_operador`, `import_traceability`, `ai_action_capabilities` |
| Acoes que a IA poderia executar | `ai_action_requests` | `ai_action_capabilities` |
| CMMS, regulatorios externos ou alocacao externa | somente dados importados; nao ha conector direto garantido | `external_integrations` |

## 1. Medicoes historicas e granularidade fina

### MPFM

Fonte principal: `measurements_active` quando existir; fallback: `measurements_curated`.

Campos importantes:

- `row_kind`: `daily`, `hourly`, `sep`, `sep_oleo_detail`, `sep_gas_detail`, `sep_agua_detail`
- `day_ref`, `hour_ref`
- `bank`, `tag`, `instrument`
- `metric_name`, `metric_value`, `metric_unit`
- `source_file`, `source_record_id`, `is_official`

Como responder:

- Por padrao, consultar todos os periodos disponiveis.
- Aplicar filtro temporal somente se o usuario pedir explicitamente mes, dia ou intervalo.
- Para perguntas por hora, filtrar `row_kind='hourly'` e `hour_ref`.
- Para pedidos de tabela horaria por ponto/TAG/banco, a ferramenta `measurement_detail` deve detectar nomes como `Riser P2`, `Riser_P2`, `B08` ou instrumento equivalente, consultar todos os periodos disponiveis salvo filtro explicito e montar tabela pivotada com oleo, gas, agua, HC, total, volumes PVT, pressao e temperatura.
- Para perguntas por dia, filtrar `row_kind='daily'`.
- Para poço/stream, usar `tag`, `bank`, `instrument` e complementar com `well_catalog_042` quando o pedido envolver poco/subsea.
- Para pressao, temperatura e densidade, buscar por `metric_name` contendo `Press`, `Temp`, `Dens`, `PVT` ou nomes equivalentes.

### Dados brutos

Fonte: `measurements_raw`.

Usar quando o usuario pedir "dado bruto", "sensor", "valor original", "payload" ou investigacao de parsing. Se nao houver linhas suficientes, avisar que a camada bruta depende do que foi persistido durante a importacao.

## 2. Separador SEP

Fontes:

- `measurements_active` / `measurements_curated` para valores consolidados e detalhes por fase.
- `sep_source_files` para arquivo fonte, hash, medidor, fase, status oficial e data de producao.
- `sep_alignments` para relacao MPFM x Separador por banco/data.

Perguntas que a IA deve fazer se faltar contexto:

- Qual periodo?
- Quer resumo ou detalhe por fase?
- Fase oleo, gas ou agua?
- Quer valores, origem do arquivo ou comparacao com MPFM?

## 3. Alarmes e eventos

Fonte principal: `alarm_records`.

Campos importantes:

- `source_kind`: diferencia PDF, workbook/importado, manual ou sistema.
- `record_type`: evento/incidente.
- `status_code`, `severity_code`, `priority_code`.
- `production_date`, `event_at`, `detected_at`.
- `bank`, `measurement_point`, `tag`, `instrument`.
- `title`, `message`, `cause`, `impact`, `immediate_action`, `corrective_action`, `evidence`.

Historico de resolucao:

- `alarm_actions`: acoes, responsavel, status, vencimento, conclusao, efetividade e verificacao.
- `alarm_audit_log`: alteracoes de campo, eventos de auditoria e notas.

Para "Origem Workbook", buscar `source_kind <> 'pdf'` ou detalhar por `source_kind` antes de filtrar.

## 4. Issues de validacao

Fontes:

- `validation_issues`: issue formal, severidade, referencia, dia e detalhes.
- `parsing_events_raw`: parser, etapa, status e `details_json`.
- `source_files_raw`: arquivo bruto relacionado.
- `files_imported`: status final do arquivo, mensagem e tipo.

Usar para explicar `unknown_tag`, `txt_rule_validation_failed`, `sep_parser_recovered_token`, duplicidades e falhas de importacao.

## 5. Prazos e atividades

Fonte atual: `deadline_items`.

Disponivel:

- assunto, categoria, inicio, vencimento, periodicidade, notas, icone, ativo/inativo.

Limitacao:

- etapas detalhadas, responsaveis por etapa e documentos anexos so existem se estiverem registrados em notas, payloads ou outros modulos documentais. Se nao estiverem, responder que ainda nao ha fonte estruturada para esse nivel.

## 6. Ativos, metadados e configuracoes

Fontes:

- `well_catalog_042`: poco, nome ANP, codigo de cadastro, tag subsea, campo e instalacao.
- `mpfm_monitoring_daily`: banco, TAG, tipo de medidor, instrumento, loop, modo operacional e alinhamento SEP.
- `pvt_params`: FE, RS, densidades standard, vigencia, fonte, autor e notas.
- `sep_alignments`: relacao banco/TAG MPFM com SEP.

Usar para perguntas como:

- quais pocos estao associados a uma tag subsea?
- qual banco/TAG possui determinada configuracao PVT?
- qual separador esta alinhado a um banco em uma data?

## 7. Reconciliacoes e calibracoes

Fontes:

- `recon_runs`: execucoes, cobertura, status, snapshots horarios, janela de teste, resumo.
- `recon_campaigns`: baseline, pos-ajuste, fator K proposto/aplicado, desvios antes/depois, status de monitoramento.
- `pvt_params`: parametros usados na campanha.

Para relatorios/certificados de calibracao em arquivo, a IA so deve afirmar acesso se o documento tiver sido importado ou referenciado em `source`, `notes`, `instructor_documents` ou outro registro da aplicacao.

## 8. Funcionalidades de acao

Estado atual:

- leitura automatica: permitida para todos os periodos disponiveis.
- escrita operacional direta: bloqueada por padrao.
- proposta de acao: registrar em `ai_action_requests` quando o fluxo da UI permitir.
- aprovacao: deve acontecer na area do Assistente IA e autoriza somente o item/escopo solicitado.

Exemplos de acoes que exigem validacao humana:

- fechar alarme;
- atualizar prazo;
- registrar atividade;
- alterar parametro PVT;
- marcar campanha de reconciliacao como aplicada.

Regra de escopo: uma aprovacao para um alarme nao autoriza outro alarme; uma aprovacao para um prazo nao autoriza outro prazo; uma aprovacao para um parametro ou medicao nao autoriza outro parametro ou medicao.

## 9. Integracoes externas

CMMS, sistemas regulatorios externos e sistemas de alocacao nao devem ser tratados como conectados automaticamente.

A IA pode responder usando:

- alarmes/acoes importadas;
- XML042 e tabelas de poco quando o assunto for ANP/XML042;
- medicoes MPFM/SEP e reconciliações para alocacao interna;
- documentos importados se existirem.

Se a pergunta exigir dado externo nao importado, responder que a integracao ainda nao esta disponivel e pedir importacao/conector.

## Manutencao do guia

Atualizar este arquivo sempre que:

- uma nova tabela for adicionada ao SQLite;
- uma nova ferramenta interna for criada em `services/ai_tools/tool_registry.py`;
- a IA passar a ter permissao de escrita aprovada;
- uma integracao externa for conectada de fato.
