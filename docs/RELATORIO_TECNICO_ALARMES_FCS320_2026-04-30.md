# Relatório Técnico - Alarmes FCS320

Data de emissão: 2026-04-30

## 1. Objetivo

Este relatório consolida a carga de alarmes FCS320 inserida na aplicação MPFM Manager a partir dos PDFs disponibilizados em:

`C:\Users\MAUAM\OneDrive - Equinor\Desktop\DPB FPSO Bacalhau - Metering - 3.2 Daily Reports\3.2.7_ALARMES_FCS_320`

O objetivo é registrar o volume importado, validar ausência de duplicidade ativa e apresentar o status atual de tratamento dos alarmes dentro da aplicação.

## 2. Fonte de Dados Carregada

Foram processados 11 PDFs de alarmes FCS320:

| Arquivo | Situação |
|---|---|
| 18-04_Alarmes FCS320.pdf | Carregado |
| 19-04_Alarmes FCS320.pdf | Carregado |
| 20-04_Alarmes FCS320.pdf | Carregado |
| 21-04_Alarmes FCS320.pdf | Carregado |
| 22-04_Alarmes FCS320.pdf | Carregado |
| 23-04_Alarmes FCS320.pdf | Carregado |
| 24-04_Alarmes FCS320.pdf | Carregado |
| 25-04_Alarmes FCS320.pdf | Carregado |
| 26-04_Alarmes FCS320.pdf | Carregado |
| 27-04_Alarmes FCS320.pdf | Carregado |
| 28-04_Alarmes FCS320.pdf | Carregado |

Antes da carga consolidada, foi criado backup do banco SQLite em:

`data/backups/mpfm_local_before_alarm_pdf_import_20260430_131227.db`

A carga PDF antiga foi mantida no banco para rastreabilidade, porém marcada como inativa. A aplicação passa a considerar como ativo somente o conjunto consolidado dos 11 PDFs acima.

## 3. Resultado da Importação

| Métrica | Quantidade |
|---|---:|
| Linhas brutas lidas dos PDFs | 5.263 |
| Eventos derivados ativos | 1.012 |
| Incidentes consolidados ativos | 879 |
| Registros ativos totais | 1.891 |
| Registros ignorados na importação | 0 |
| Registros PDF antigos desativados | 231 |

Período de produção identificado nos registros ativos: 2026-01-22 a 2026-04-28.

Observação: embora os arquivos sejam relatórios diários de abril, eles contêm alarmes históricos ainda relacionados ao estado atual do FCS320. Por isso a base ativa inclui eventos com data de produção desde janeiro.

## 4. Validação de Duplicidade

Foram aplicadas duas validações sobre os registros PDF ativos:

| Critério de validação | Resultado |
|---|---:|
| Duplicidade por identidade técnica (`source_kind`, `source_ref`, `source_sheet`, `record_type`, `external_code`) | 0 grupos duplicados |
| Duplicidade por mesmo dia, tipo, ponto, tag, data/hora do evento e título | 0 grupos duplicados |

Conclusão: não há dados duplicados ativos para o mesmo dia na carga consolidada.

É importante separar duplicidade de recorrência operacional. A aplicação pode registrar múltiplas ocorrências no mesmo dia para um mesmo medidor quando elas possuem horários/eventos distintos. Isso é esperado e representa reincidência ou continuidade operacional do alarme, não duplicação de carga.

Também é esperado que uma mesma condição apareça como `event` e como `incident`: o registro `event` representa a ocorrência derivada, enquanto `incident` representa a consolidação operacional do agrupamento.

## 5. Status Atual de Tratamento

### 5.1 Visão por tipo

| Tipo | Total ativo | Fechado | Aberto | Crítico | Warning |
|---|---:|---:|---:|---:|---:|
| Eventos | 1.012 | 1.004 | 8 | 908 | 104 |
| Incidentes | 879 | 871 | 8 | 846 | 33 |

Status operacional atual:

- 99,2% dos eventos estão fechados.
- 99,1% dos incidentes estão fechados.
- Permanecem 8 eventos e 8 incidentes em aberto.
- Todos os registros em aberto são críticos, urgentes e classificados como `Communication status`.
- Todos os registros em aberto estão concentrados em 2026-04-28.

### 5.2 Registros em aberto

| Tipo | Data/hora | Ponto de medição | Alarme | Severidade | Prioridade | Ocorrências |
|---|---|---|---|---|---|---:|
| Incidente | 2026-04-28 23:30:09 | Bank05.Stream03.MeterA | Communication status | critical | urgent | 1 |
| Evento | 2026-04-28 23:30:09 | Bank05.Stream03.MeterA | Communication status | critical | urgent | 2 |
| Incidente | 2026-04-28 23:30:02 | Bank15.Stream02.MeterA | Communication status | critical | urgent | 1 |
| Evento | 2026-04-28 23:30:02 | Bank15.Stream02.MeterA | Communication status | critical | urgent | 2 |
| Incidente | 2026-04-28 22:30:13 | Bank08.Stream02.MeterA | Communication status | critical | urgent | 1 |
| Evento | 2026-04-28 22:30:13 | Bank08.Stream02.MeterA | Communication status | critical | urgent | 2 |
| Incidente | 2026-04-28 22:30:11 | Bank10.Stream01.MeterA | Communication status | critical | urgent | 1 |
| Incidente | 2026-04-28 22:30:11 | Bank03.Stream01.MeterA | Communication status | critical | urgent | 1 |
| Evento | 2026-04-28 22:30:11 | Bank10.Stream01.MeterA | Communication status | critical | urgent | 2 |
| Evento | 2026-04-28 22:30:11 | Bank03.Stream01.MeterA | Communication status | critical | urgent | 2 |
| Evento | 2026-04-28 22:30:09 | Bank13.Stream02.MeterA | Communication status | critical | urgent | 2 |
| Incidente | 2026-04-28 22:30:08 | Bank08.Stream01.MeterA | Communication status | critical | urgent | 1 |
| Evento | 2026-04-28 22:30:08 | Bank08.Stream01.MeterA | Communication status | critical | urgent | 2 |
| Incidente | 2026-04-28 22:30:02 | Bank03.Stream02.MeterA | Communication status | critical | urgent | 1 |
| Evento | 2026-04-28 22:30:02 | Bank03.Stream02.MeterA | Communication status | critical | urgent | 2 |
| Incidente | 2026-04-28 21:51:25 | Bank13.Stream02.MeterA | Communication status | critical | urgent | 2 |

## 6. Distribuição por Dia

| Data de produção | Eventos | Incidentes | Abertos | Fechados | Críticos | Warning |
|---|---:|---:|---:|---:|---:|---:|
| 2026-01-22 | 1 | 1 | 0 | 2 | 0 | 2 |
| 2026-01-29 | 17 | 16 | 0 | 33 | 30 | 3 |
| 2026-02-07 | 2 | 2 | 0 | 4 | 0 | 4 |
| 2026-02-08 | 1 | 1 | 0 | 2 | 0 | 2 |
| 2026-02-12 | 1 | 1 | 0 | 2 | 0 | 2 |
| 2026-03-01 | 1 | 1 | 0 | 2 | 0 | 2 |
| 2026-03-03 | 1 | 1 | 0 | 2 | 0 | 2 |
| 2026-03-17 | 1 | 1 | 0 | 2 | 2 | 0 |
| 2026-03-25 | 1 | 1 | 0 | 2 | 0 | 2 |
| 2026-04-10 | 1 | 1 | 0 | 2 | 0 | 2 |
| 2026-04-15 | 1 | 1 | 0 | 2 | 0 | 2 |
| 2026-04-17 | 5 | 4 | 0 | 9 | 0 | 9 |
| 2026-04-18 | 17 | 14 | 0 | 31 | 20 | 11 |
| 2026-04-19 | 9 | 9 | 0 | 18 | 16 | 2 |
| 2026-04-20 | 103 | 88 | 0 | 191 | 179 | 12 |
| 2026-04-21 | 107 | 98 | 0 | 205 | 195 | 10 |
| 2026-04-22 | 109 | 92 | 0 | 201 | 188 | 13 |
| 2026-04-23 | 109 | 95 | 0 | 204 | 190 | 14 |
| 2026-04-24 | 104 | 86 | 0 | 190 | 181 | 9 |
| 2026-04-25 | 98 | 85 | 0 | 183 | 181 | 2 |
| 2026-04-26 | 99 | 93 | 0 | 192 | 189 | 3 |
| 2026-04-27 | 105 | 93 | 0 | 198 | 190 | 8 |
| 2026-04-28 | 119 | 95 | 16 | 198 | 193 | 21 |

## 7. Pontos de Medição Mais Recorrentes

| Ponto de medição | Tipo | Total | Abertos | Críticos |
|---|---|---:|---:|---:|
| Bank13.Stream02.MeterA | Evento | 147 | 1 | 109 |
| Bank03.Stream01.MeterA | Evento | 124 | 1 | 109 |
| Bank15.Stream02.MeterA | Evento | 121 | 1 | 109 |
| Bank08.Stream01.MeterA | Evento | 117 | 1 | 109 |
| Bank10.Stream01.MeterA | Evento | 114 | 1 | 109 |
| Bank08.Stream01.MeterA | Incidente | 113 | 1 | 109 |
| Bank08.Stream02.MeterA | Evento | 113 | 1 | 109 |
| Bank03.Stream01.MeterA | Incidente | 111 | 1 | 108 |
| Bank03.Stream02.MeterA | Evento | 111 | 1 | 109 |
| Bank03.Stream02.MeterA | Incidente | 111 | 1 | 109 |
| Bank05.Stream03.MeterA | Evento | 111 | 1 | 109 |
| Bank08.Stream02.MeterA | Incidente | 111 | 1 | 109 |
| Bank05.Stream03.MeterA | Incidente | 110 | 1 | 109 |
| Bank10.Stream01.MeterA | Incidente | 109 | 1 | 107 |
| Bank15.Stream02.MeterA | Incidente | 109 | 1 | 109 |
| Bank13.Stream02.MeterA | Incidente | 54 | 1 | 50 |

## 8. Leitura Técnica do Tratamento Atual

A aplicação está tratando os alarmes importados em dois níveis complementares:

1. Evento: ocorrência derivada diretamente do log bruto do PDF.
2. Incidente: consolidação operacional de uma ou mais ocorrências relacionadas.

Para a carga atual, o tratamento está majoritariamente concluído: todos os registros até 2026-04-27 estão fechados. O resíduo operacional está concentrado em 2026-04-28, composto por alarmes críticos de comunicação em medidores específicos.

Os alarmes abertos indicam perda ou instabilidade de comunicação em pontos de medição. Como estão marcados como `critical` e `urgent`, devem ser tratados como pendência operacional prioritária, especialmente nos pontos:

- Bank03.Stream01.MeterA
- Bank03.Stream02.MeterA
- Bank05.Stream03.MeterA
- Bank08.Stream01.MeterA
- Bank08.Stream02.MeterA
- Bank10.Stream01.MeterA
- Bank13.Stream02.MeterA
- Bank15.Stream02.MeterA

## 9. Observações Técnicas

- A carga ativa foi consolidada em uma única referência de origem iniciada por `pdf:` e contendo os 11 nomes de arquivos importados.
- A carga PDF antiga permanece no banco como histórico inativo, com 119 eventos e 112 incidentes.
- O campo `bank` ficou vazio nos registros derivados desta importação; para análise operacional, o relatório utiliza `measurement_point`, que contém o identificador do banco/stream/medidor.
- As famílias técnicas dos eventos foram classificadas em `critico_comunicacao`, `geral_operacional` e `hardware_instrumentacao`; os incidentes consolidados ainda não exibem família técnica preenchida em todos os casos.

## 10. Conclusão

A carga consolidada dos alarmes FCS320 foi concluída com sucesso, sem duplicidade ativa e com rastreabilidade preservada por backup e registros antigos inativos.

O estado atual da aplicação mostra 1.891 registros ativos derivados dos PDFs, sendo 1.875 fechados e 16 ainda abertos. Os 16 registros abertos correspondem a 8 eventos e 8 incidentes críticos de comunicação, todos concentrados em 2026-04-28.

Recomendação técnica: priorizar a análise dos alarmes `Communication status` abertos em 2026-04-28 e, após confirmação operacional, registrar fechamento ou ação corretiva diretamente na aplicação para manter o painel de alarmes alinhado ao estado real da medição.