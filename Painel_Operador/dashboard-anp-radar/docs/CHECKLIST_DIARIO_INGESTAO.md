# Checklist Diario Bacalhau - Mapeamento de Ingestao

Arquivo analisado:

`C:\Users\mauri\OneDrive\Documentos\Painel_Operador\Bacalhau - Checklist Diario_junho_26.xlsm`

## Resultado da leitura

- Workbook com 75 abas.
- 33 abas foram classificadas como importaveis para o modulo operacional:
  - abas principais: `Ocurrences`, `Lab-Report`, `API`, `Tank `, `Off Spec Tank`, `MPFM Subsea x Fiscal- Óleo`, `Balanço de Gás`;
  - abas de faixa por medidor: `*-Fx`;
  - abas diarias: `01` a `14` e `01d`.
- Abas `.xml`, `XML.*` e `S600.*` sao referencia/migracao: em geral representam dados que a aplicacao deve obter dos XMLs e relatórios ja carregados, nao do checklist como fonte primaria.

## Importacao implementada

Foram criadas tabelas SQLite dedicadas:

- `painel_operador_daily_checklist_runs`
- `painel_operador_daily_checklist_rows`

A carga atual importou 18.024 linhas preservando:

- arquivo de origem e hash;
- aba, linha e dominio;
- data identificada quando disponivel;
- tag quando identificavel;
- status, responsavel, titulo/metrica;
- `payload_json` com os valores e cabecalhos completos da linha.

Rotas disponiveis:

- `GET /api/painel-operador/daily-checklist-summary`
- `GET /api/painel-operador/daily-checklist/inspect?path=...`
- `POST /api/painel-operador/daily-checklist/import`
- `GET /api/painel-operador/daily-checklist`

Frontend:

- Aba `Painel Operador > Checklist Diario`.
- Permite informar caminho, inspecionar workbook, importar e consultar linhas por aba, data, tag e busca textual.

## Mapeamento por aba

| Aba | Papel operacional | Ja existe parcialmente no app? | Origem futura preferencial |
| --- | --- | --- | --- |
| `Ocurrences` | Registro de ocorrencias, NFSM, SAP, responsavel, status e acao executada. | Parcial: alarmes/eventos e propostas existem, mas nao com toda a tratativa manual. | Checklist + fluxo de ocorrencias nativo. |
| `Lab-Report` | API, densidade, BSW, metodo e referencias de laboratorio/analisador. | Parcial: PVT/logbook e dados de analise existem, mas sem ingestao direta dessa aba. | Laudos/analises + reconciliacao com volume fiscal. |
| `API` | API/BSW ponderados por volume. | Parcial. | Calculo nativo usando Lab-Report + volumes fiscais. |
| `Tank ` | Abertura/fechamento de tanque, delta tanque, fiscal meter, delta percentual e observacoes. | Nao completo. | Ingestao propria + volumes fiscais/ANP. |
| `Off Spec Tank` | Volume em tanque offspec e indicacao de producao direcionada. | Nao completo. | Ingestao propria; XML nao traz o motivo operacional. |
| `MPFM Subsea x Fiscal- Óleo` | Comparacao MPFM subsea x medidor fiscal, reprocessamento e comentarios. | Parcial: MPFM e fiscal ja existem, falta a visao consolidada/comentada. | Recriar no app com `measurements_curated` + fiscal/ANP + comentarios. |
| `Balanço de Gás` | Entradas operacionais x saidas fiscais/injecao, por dia. | Parcial: dados de gas existem, falta materializar o balanco continuo. | XMLs/ANP + medidores operacionais + regra de balanco. |
| `*-Fx` | Controle de faixa, PAM, min/max, pressao, temperatura, vazao e comentarios por medidor. | Sim, parcialmente: `painel_operador_measurement_limits` e monitor tecnico. | Normalizar para limites/PAM e grafico continuo. |
| `01` a `14` | Evidencia diaria com configuracoes CV, XMLs, reports e verificacoes. | Parcial: CV snapshots, XMLs e medições ja existem. | Usar como validacao/migracao ate a aplicacao recriar a rotina diaria. |

## Lacunas para fechamento funcional

1. Normalizar linhas importadas em tabelas especificas por dominio: ocorrencias, lab/API/BSW, tanques, offspec, MPFM x fiscal e balanco de gas.
2. Recriar no app os calculos que hoje estao em formulas do Excel:
   - API/BSW ponderado;
   - delta tanque x fiscal;
   - producao offspec;
   - MPFM subsea x fiscal;
   - balanco de gas operacional x fiscal/injecao.
3. Ligar os dados normalizados aos graficos ja existentes em `Dados Medidos` e `Limites & CV`.
4. Fazer as telas de preenchimento nativo substituirem o Excel no fluxo diario, mantendo exportacao/auditoria quando necessario.

