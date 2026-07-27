# Radar ANP - Regras iniciais de validação

Este documento registra as regras que o radar deve aplicar. Cada regra precisa de `rule_id`, fonte, cálculo, severidade e evidência.

## 1. Envio e recebimento ANP

| Regra | Condição | Severidade |
|---|---|---|
| `xml_expected_missing` | família XML esperada para a data não foi localizada | crítico |
| `xml_not_received_anp` | XML existe, mas export ANP não contém o registro | crítico |
| `xml_anp_value_mismatch` | valor XML diferente do Painel ANP acima da tolerância | crítico |
| `raw_xml_missing_source` | XML/ANP batem, mas raw direto não foi localizado | atenção |
| `raw_xml_value_mismatch` | raw diferente do XML acima da tolerância | crítico |

## 2. Alarmes/eventos e evidência analítica

| Regra | Condição | Evidência esperada | Severidade |
|---|---|---|---|
| `density_event_without_lab` | evento altera densidade, mas não existe laudo compatível | lab report/densidade | crítico |
| `chromatography_event_without_report` | evento altera cromatografia, mas não existe cromatografia compatível | laudo cromatográfico | crítico |
| `pvt_event_without_report` | evento altera PVT/modelo, mas não existe relatório PVT | relatório PVT ou MPFM | crítico |
| `bsw_event_without_report` | evento altera BSW/fator, mas não existe boletim BSW/XML 040 | boletim BSW | atenção/crítico |
| `mf_kf_event_without_calibration` | evento altera meter factor/K-factor sem calibração/provação | certificado/provação | crítico |
| `range_event_without_datasheet` | evento altera range/PAM/limite sem datasheet ou gestão de mudança | PAM/datasheet/MOC | crítico |

### Correlacionador evento -> evidência implementado

O dashboard já executa o correlacionador `evento -> evidência` com busca por arquivo candidato e leitura de conteúdo.

Entrada:

- arquivos `AlarmsAndEvents*.txt`;
- linhas com padrão `Parameter ... was changed from ... to ... by ...`;
- arquivos candidatos nas fontes configuradas de físico-química, calibração, incerteza, PAM/equipamentos, planos e normas.

Classificação:

- densidade/BSW;
- PVT/propriedades de fluido;
- cromatografia/composição do gás;
- calibração/fator de medidor;
- PAM/limites/faixas;
- incerteza.

Status:

- `ok`: evidência candidata forte e conteúdo extraído confirma parâmetro e valor novo próximos;
- `warn`: há evidência candidata ou apoio textual, mas falta confirmação forte de valor/ponto/validade;
- `critical`: nenhuma evidência candidata encontrada.

A versão atual extrai conteúdo de PDF, planilhas XLSX/XLSM, DOCX, ZIP e arquivos texto/XML/CSV/HTML. O registro de auditoria inclui estado da evidência (`confirmed`, `supporting`, `candidate`), motivo, hits de conteúdo e trecho extraído quando disponível. A próxima evolução deve melhorar leitura de tabelas em PDF, confirmação numérica com tolerância, página/linha/aba e validade documental.

## 3. Limites, PAM e faixa calibrada

| Regra | Condição | Severidade |
|---|---|---|
| `value_outside_alarm_limits` | pressão/temperatura/DP fora do limite inferior/superior | crítico |
| `value_outside_pam` | medição fora do PAM/faixa operacional | crítico |
| `value_outside_calibrated_range` | variável fora da faixa calibrada do certificado | crítico |
| `missing_calibrated_range` | ponto ativo sem faixa calibrada cadastrada | atenção |
| `missing_datasheet_pam` | ponto ativo sem datasheet/PAM | atenção |

## 4. Calibração e validade

| Regra | Condição | Severidade |
|---|---|---|
| `calibration_expired` | certificado vencido na data operacional | crítico |
| `calibration_due_soon` | certificado vence dentro da janela configurada | atenção |
| `serial_mismatch` | série no certificado difere da série no XML/Painel | crítico |
| `missing_certificate` | instrumento ativo sem certificado | atenção/crítico |

## 5. Incerteza

| Regra | Condição | Severidade |
|---|---|---|
| `daily_uncertainty_above_limit` | incerteza calculada diária > limite permitido | crítico |
| `missing_uncertainty_model` | ponto ativo sem memória/cálculo de incerteza | atenção |
| `uncertainty_version_outdated` | versão de memória anterior à alteração relevante | atenção/crítico |

## 6. Análises físico-químicas e plano de coleta

| Regra | Condição | Severidade |
|---|---|---|
| `sampling_plan_due` | análise/coleta esperada não executada até a data limite | crítico |
| `analysis_missing` | evento ou período requer análise, mas resultado não existe | crítico |
| `lab_online_bsw_mismatch` | BSW lab x online diverge acima da tolerância | atenção/crítico |
| `composition_outdated` | cromatografia usada fora da validade/período | atenção/crítico |
| `density_outdated` | densidade usada fora da validade/período | atenção/crítico |

## 7. Falhas de medição

| Regra | Condição | Severidade |
|---|---|---|
| `failure_open_overdue` | NFSM aberta com previsão vencida | crítico |
| `failure_volume_without_methodology` | volume de falha sem metodologia/evidência | crítico |
| `failure_related_event_missing` | falha menciona evento/dado sem arquivo correspondente | atenção/crítico |

## 8. Dossiê do ponto

O dossiê deve consolidar:

- cadastro do ponto;
- séries CV/raw;
- XMLs enviados;
- recebimento Painel ANP;
- alarmes/eventos;
- certificados;
- incerteza;
- análises;
- plano de coleta;
- falhas;
- pendências e recomendações.
