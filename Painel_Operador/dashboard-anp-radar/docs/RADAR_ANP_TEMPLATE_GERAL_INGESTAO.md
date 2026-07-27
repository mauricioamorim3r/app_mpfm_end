# Radar ANP - Template geral de ingestao

Data de referencia: 2026-07-03

Este template define os dados minimos para alimentar o Radar ANP quando a extracao automatica ainda nao existir ou quando for necessario complementar uma fonte. O mesmo contrato deve orientar planilhas, formularios, APIs e propostas da IA.

## Regras gerais

- Uma linha deve representar uma observacao auditavel.
- Campos de data devem usar `YYYY-MM-DD`; data e hora devem usar `YYYY-MM-DD HH:MM:SS`.
- Numeros devem ser armazenados em formato numerico, sem unidade no mesmo campo.
- Toda linha deve ter origem: arquivo, aba/linha quando aplicavel, responsavel ou observacao.
- Campos desconhecidos devem ficar vazios, nao preenchidos com suposicao.
- Quando a IA extrair dado de documento, ela deve preencher os campos de evidencia e gerar proposta antes de gravar como aprovado.

## Abas do arquivo Excel

| Aba | Finalidade |
| --- | --- |
| `fontes` | pastas, arquivos, sistemas e grupos de origem usados na ingestao |
| `pontos_medicao` | cadastro tecnico e regulatorio dos pontos |
| `medicoes_raw` | valores brutos ou consolidados diarios por origem |
| `xml_anp` | XMLs/pacotes enviados para ANP |
| `painel_anp` | linhas recebidas/exportadas do Painel do Operador |
| `limites_pam` | limites, PAM, faixa calibrada e alarmes |
| `calibracoes` | certificados, validade e estado de calibracao |
| `incertezas` | estudos e valores de incerteza por ponto/metrica |
| `analises_fq` | densidade, cromatografia, PVT, BSW e analises relacionadas |
| `eventos_parametros` | alarmes, eventos e mudancas de parametro |
| `requisitos_regulatorios` | regra, prazo, periodicidade e base normativa |
| `pendencias_acoes` | pendencias, baixa, recomendacao e decisao humana |
| `auditoria` | trilha de extracao, regra, evidencia e aprovacao |

## Validacoes minimas

- Todo valor enviado no XML deve poder apontar para uma origem raw, justificativa ou regra de consolidacao.
- Todo valor recebido no Painel ANP deve ser reconciliado com XML enviado ou marcado como `anp_only`.
- Toda mudanca de parametro que afete medicao deve procurar evidencia analitica ou documental.
- Todo limite/PAM deve ter fonte e validade.
- Todo certificado vencido ou sem data deve gerar pendencia.
- Toda pendencia baixada deve guardar decisao humana.
- Toda proposta da IA deve guardar evidencia e escopo antes de qualquer gravacao.

## Resultado esperado da ingestao

Depois da ingestao, o Radar deve produzir:

- calendario dos dias carregados e faltantes;
- fechamento diario por ponto/familia/fluido;
- comparacao raw x XML x ANP;
- alertas tecnicos e regulatorios;
- checklist regulatorio;
- dossie por ponto;
- fila de propostas auditaveis;
- trilha de auditoria reprocessavel.

## Campos por aba

O arquivo `templates/Radar_ANP_Template_Geral_Ingestao.xlsx` materializa estas abas com cabecalhos, descricoes e exemplos. Os campos essenciais sao:

- `fontes`: `source_id`, `source_group`, `path`, `recursive`, `expected_extensions`, `owner_area`, `notes`.
- `pontos_medicao`: `point_id`, `tag`, `family`, `fluid`, `measurement_type`, `meter_type`, `flow_computer`, `installation`, `active_from`, `active_to`, `source_ref`.
- `medicoes_raw`: `production_date`, `tag`, `source_kind`, `metric_name`, `metric_value`, `metric_unit`, `period_start`, `period_end`, `quality_status`, `source_file`, `source_row`.
- `xml_anp`: `xml_id`, `family`, `reference_date`, `tag`, `sent_value`, `value_unit`, `sent_at`, `protocol`, `file_path`, `validation_status`.
- `painel_anp`: `export_id`, `family`, `reference_date`, `tag`, `received_value`, `value_unit`, `status_anp`, `source_file`, `source_sheet`, `source_row`.
- `limites_pam`: `tag`, `metric_name`, `value_unit`, `calibrated_min`, `calibrated_max`, `pam_min`, `pam_max`, `alarm_low`, `alarm_high`, `valid_from`, `valid_to`, `source_ref`, `approval_status`.
- `calibracoes`: `tag`, `certificate_id`, `calibration_date`, `valid_until`, `result_status`, `lab_or_vendor`, `source_file`, `notes`.
- `incertezas`: `tag`, `metric_name`, `uncertainty_value`, `coverage_factor`, `confidence_level`, `valid_from`, `valid_to`, `source_file`.
- `analises_fq`: `sample_id`, `tag`, `sample_date`, `analysis_type`, `parameter_name`, `parameter_value`, `parameter_unit`, `used_from`, `source_file`.
- `eventos_parametros`: `event_id`, `event_at`, `tag`, `parameter_name`, `previous_value`, `current_value`, `event_type`, `severity`, `source_file`, `expected_evidence_type`.
- `requisitos_regulatorios`: `requirement_id`, `requirement_title`, `normative_base`, `applies_to`, `periodicity`, `deadline_rule`, `mandatory_fields`, `evidence_expected`.
- `pendencias_acoes`: `pendency_id`, `calendar_date`, `tag`, `pendency_type`, `severity`, `status`, `recommended_action`, `decision_by`, `decision_at`, `decision_note`.
- `auditoria`: `audit_id`, `business_key`, `source_path`, `source_hash`, `extracted_at`, `parser_name`, `parser_version`, `rule_id`, `rule_version`, `evidence_ref`, `confidence`, `human_decision_status`.
