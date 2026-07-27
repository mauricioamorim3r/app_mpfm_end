# Radar ANP - Correlacionador evento -> evidencia

Este documento descreve o correlacionador que cruza eventos de alteracao de parametro com documentos tecnicos existentes nas pastas configuradas. A versao atual ja possui leitura de conteudo para PDF, planilhas, DOCX, ZIP e arquivos texto.

## Objetivo

Detectar quando um parametro operacional foi alterado no computador de vazao ou sistema associado e verificar se existe evidencia documental compativel.

Exemplos:

- viscosidade dinamica alterada -> relatorio PVT esperado;
- expoente isentropico alterado -> PVT/composicao esperada;
- densidade ou BSW alterado -> laudo/boletim esperado;
- meter factor ou K-factor alterado -> calibracao/provacao esperada;
- limite, range ou PAM alterado -> PAM, datasheet, memorial ou aprovacao esperada.

## Fontes lidas

Eventos:

- `AlarmsAndEvents*.txt` nas pastas configuradas como `alarmsEvents` e `dailyReports`.

Evidencias:

- `physchem`;
- `calibration`;
- `uncertainty`;
- `equipmentDocs`;
- `samplingPlans`;
- `regulations`;
- `dailyReports`.

Extensoes consideradas:

- `.pdf`, `.xlsx`, `.xlsm`, `.xls`, `.docx`, `.doc`, `.zip`, `.xml`, `.txt`, `.csv`.

Observacao: a versao atual extrai conteudo de `.pdf`, `.xlsx`, `.xlsm`, `.docx`, `.zip`, `.xml`, `.txt`, `.csv`, `.html` e `.htm`. Arquivos `.xls` antigos ainda entram no indice, mas a extracao profunda deles fica como melhoria futura.

## Regra de entrada

Um evento entra no radar quando a linha do TXT possui o padrao:

```text
Parameter ... was changed from ... to ... by ...
```

Eventos comuns de transicao de alarme, como `from Normal to Alarm`, sao contabilizados como contexto, mas nao entram como alteracao documental obrigatoria.

## Classificacao do evento

O parametro alterado e classificado por palavras-chave.

| Tipo | Palavras-chave do parametro | Evidencia esperada |
|---|---|---|
| `density_bsw` | density, densidade, bsw, water cut | laudo, BSW, densidade, boletim |
| `pvt` | pvt, viscos, isentropic, compress, z factor | relatorio PVT |
| `chromatography` | chromat, cromat, composition, methane, ethane, propane, butane, pentane, hexane, heptane, octane, nonane, decane, nitrogen, oxygen, carbon dioxide, metano | cromatografia/composicao |
| `calibration` | meter factor, k factor, proving, calibr | certificado/provacao/calibracao |
| `pam_limits` | range, limit, limite, cutoff, pressure | PAM, datasheet, memorial |
| `uncertainty` | uncert, incerteza | memoria ou calculo de incerteza |

## Pontuacao v1

Cada evidencia candidata recebe uma pontuacao.

| Evidencia | Pontos |
|---|---:|
| Tipo documental esperado bate com o evento | 3 |
| Tag/equipamento aparece no evento e no documento | 4 |
| Data do documento ate 7 dias do evento | 3 |
| Data do documento ate 45 dias do evento | 2 |
| Data do documento no mesmo ciclo anual | 1 |
| Contexto do sistema aparece no caminho/documento | 1 |

Status:

- `ok`: melhor candidata com pontuacao igual ou maior que 7;
- `warn`: existe candidata, mas pontuacao menor que 7;
- `critical`: nenhuma candidata encontrada.

## Confirmacao de conteudo v2

Depois da pontuacao inicial, o radar tenta abrir o conteudo dos documentos candidatos.

Extratores:

- PDF: primeiras paginas via `pdfplumber`;
- XLSX/XLSM: primeiras abas e linhas via `openpyxl`;
- DOCX: paragrafos e primeiras tabelas;
- ZIP: nomes dos arquivos internos e conteudo de entradas texto/XML/CSV/HTML;
- TXT/XML/CSV/HTML: leitura direta.

Estados de evidencia:

| Estado | Condicao | Uso no status |
|---|---|---|
| `confirmed` | parametro e valor novo aparecem proximos no conteudo extraido | pode virar `ok` |
| `supporting` | conteudo contem parametro, termo documental ou parametro/valor distantes | permanece `warn` |
| `candidate` | apenas nome/caminho/tipo indicam compatibilidade | permanece `warn` |
| `missing` | nenhuma evidencia candidata encontrada | `critical` |

A regra de proximidade evita marcar como `ok` quando o valor aparece em outro ponto do documento sem relacao clara com o parametro.

Cache:

- o texto extraido fica em `data/evidence_text_cache.json`;
- a chave do cache usa caminho absoluto, data de modificacao e tamanho do arquivo;
- se o arquivo mudar, o texto e extraido novamente;
- na base atual, apos o cache inicial, o reprocessamento ficou em cerca de 27,7 segundos.

## Saida no JSON

O resultado fica em `src/data/dashboard-data.json`, chave `eventEvidenceRadar`.

Campos principais:

- `summary.eventFilesScanned`;
- `summary.eventLinesScanned`;
- `summary.parameterChanges`;
- `summary.evidenceIndexed`;
- `summary.ok`;
- `summary.warn`;
- `summary.critical`;
- `summary.confirmed`;
- `summary.supporting`;
- `summary.candidateOnly`;
- `events[].timestamp`;
- `events[].parameter`;
- `events[].oldValue`;
- `events[].newValue`;
- `events[].expectedEvidenceLabels`;
- `events[].evidenceState`;
- `events[].evidenceCandidates[]`.

Campos relevantes em `events[].evidenceCandidates[]`:

- `contentState`;
- `contentReason`;
- `contentHits`;
- `contentDistance`;
- `snippet`;
- `extractor`;
- `baseScore`;
- `score`.

## Resultado atual da base recebida

No reprocessamento de 2026-06-16:

- 1.258 arquivos de eventos varridos;
- 35.778 linhas de evento lidas;
- 57 alteracoes de parametro identificadas;
- 1.711 evidencias candidatas indexadas;
- 4 evidencias confirmadas por conteudo;
- 53 evidencias com apoio textual;
- 4 casos em `ok`;
- 53 casos em `warn`;
- 0 casos em `critical`.

Interpretacao: nao ha evento sem evidencia candidata, mas a maior parte ainda precisa de confirmacao mais profunda de valor, pagina/aba, validade e relacao direta com o ponto. Por isso permanecem como atencao.

## Proxima versao

Para transformar mais `warn` em `ok` com robustez de auditoria, a proxima versao deve:

- ler mais paginas de PDFs tecnicos quando necessario;
- extrair tabelas de PDF com pagina e coordenada;
- confirmar valor antigo/novo com tolerancia numerica;
- confirmar ponto, corrente, equipamento ou tag;
- confirmar data de validade/aplicacao;
- registrar pagina, aba, linha ou trecho usado como evidencia;
- diferenciar relatorio tecnico, configuracao do computador de vazao e evidencia de aprovacao/MOC.
