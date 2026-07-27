# Migracao Radar ANP para MPFM NOVO

Data de referencia: 2026-07-03

Este documento registra a consolidacao das funcionalidades discutidas para o Radar ANP dentro do projeto `C:\MPFM\NOVO` e do modulo `C:\MPFM\NOVO\Painel_Operador`.

## Pasta oficial de execucao

A aplicacao integrada deve ser executada a partir de:

- `C:\MPFM\NOVO`

O modulo Radar/Painel do Operador usado como fonte operacional fica em:

- `C:\MPFM\NOVO\Painel_Operador\dashboard-anp-radar`

A pasta antiga em OneDrive deve ser tratada como fonte historica/material recebido. Ela nao deve sobrescrever a configuracao do destino, porque o destino ja esta normalizado para `C:\MPFM\NOVO\Painel_Operador`.

## O que foi migrado para o MPFM principal

| Area | Arquivos no MPFM | Funcionalidade |
| --- | --- | --- |
| Backend FastAPI | `routes/painel_operador_routes.py` | APIs do Painel Operador, monitor tecnico, calendario, staging e decisao de pendencias |
| Servico de staging | `services/painel_operador/staging_service.py` | Leitura do contrato Radar, importacao ANP, catalogo, limites/CV, calendario e baixa auditavel de pendencias |
| Banco local | `db_schema.py` | Tabelas `painel_operador_*`, limites/PAM, snapshots CV e propostas/pendencias |
| Frontend integrado | `index.html`, `static/app.painel_operador.js`, `static/app.layout.css` | Tela `Painel do Operador` dentro do MPFM com ingestao, fontes, ANP, dados medidos, limites/CV, comparacao, calendario, propostas e staging |
| Submodulo Dashboard ANP Radar | `index.html`, `static/app.painel_operador.js`, `static/app.layout.css` | Recriacao integrada das telas Operacao, Trilha E2E, Calendario, Prazos, Propostas, Configuracao, Pergunte ao Radar e Dossie do ponto |
| Assistente IA | `services/ai_tools/tool_registry.py`, `docs/AI_ASSISTANT_DATA_GUIDE.md` | IA orientada a consultar `painel_operador_*`, explicar alertas e propor acoes sem escrita direta |
| Contrato mestre | `docs/RADAR_ANP_PLANO_MESTRE.md` | Especificacao operacional do Radar ANP inteligente |
| Template de ingestao | `docs/RADAR_ANP_TEMPLATE_GERAL_INGESTAO.md`, `templates/Radar_ANP_Template_Geral_Ingestao.xlsx` | Estrutura manual/contingencia para dados brutos, XML, Painel ANP, limites, incerteza, analises, eventos, requisitos e auditoria |

## O que foi sincronizado para o modulo `Painel_Operador/dashboard-anp-radar`

| Arquivo | Motivo |
| --- | --- |
| `docs/RADAR_ANP_PLANO_MESTRE.md` | Manter o contrato mestre junto do motor Radar original |
| `docs/RADAR_ANP_TEMPLATE_GERAL_INGESTAO.md` | Manter a definicao de campos junto dos parsers/templates |
| `templates/Radar_ANP_Template_Geral_Ingestao.xlsx` | Permitir carga manual/contingencia tambem no modulo isolado |
| `MANIFESTO_ARQUIVOS_APLICACAO.md` | Atualizado para citar os novos artefatos |
| `docs/ai-operational-context.md` | Atualizado para apontar o plano mestre/template como fonte operacional da IA |

## Funcionalidades alinhadas no MPFM

- Configuracao de 14 grupos de fontes com busca em subpastas.
- Catalogo de arquivos do Painel Operador.
- Importacao dos exports ANP principais.
- Staging de fontes, pontos, comparacoes, evidencias, alertas, propostas, calendario e pendencias.
- Apuracao diaria de producao por arquivos, Fiscal/Radar, Painel ANP e MPFM diario.
- Comparacao ANP x staging com estados `matched`, `value_mismatch`, `anp_only`, `staging_only` e `not_comparable`.
- Monitor tecnico de limites/PAM, faixa calibrada, incerteza, snapshots CV e eventos.
- Cards visuais do monitor tecnico para risco de faixa/PAM, incerteza, eventos CV e propostas pendentes.
- Calendario visual de dias carregados, faltantes e com pendencias.
- Baixa/adiamento de pendencia por tela, gravando somente decisao local auditavel.
- Assistente IA instruido a trabalhar em modo leitura e criar propostas aprovaveis para qualquer escrita.
- Aba `Dashboard ANP Radar` abaixo de `Painel do Operador`, sem iframe e sem depender do Vite/React original.
- Telas do Radar original recriadas no MPFM usando `/api/painel-operador/data`, staging SQLite e `/api/ai/ask`.
- Filtros globais por dia, ponto/tag e busca textual aplicados nas telas internas do Radar.
- Tela `Pergunte ao Radar` integrada ao Assistente IA do MPFM com contexto do Painel Operador/Radar ANP.

## Itens que nao devem ser copiados da pasta antiga

- `node_modules`, `dist`, `.playwright-mcp`, `.vscode`, caches e logs temporarios.
- `config/data-sources.json` antigo apontando para OneDrive.
- Dados fonte soltos quando o objetivo for transportar apenas a aplicacao. Os dados fonte devem ficar em pastas configuradas na tela de ingestao.

## Validacoes recomendadas apos migracao

1. Executar `C:\MPFM\NOVO\iniciar.bat` ou `python server.py`.
2. Abrir `http://127.0.0.1:8765`.
3. Entrar na tela `Painel do Operador`.
4. Clicar em `Atualizar`, `Reindexar fontes`, `Importar exports ANP`, `Sincronizar contrato` e `Processar Limites/CV`.
5. Conferir as abas `Limites & CV` e `Calendario`.
6. Testar uma baixa de pendencia em item real somente quando houver decisao operacional.

## Observacao de auditoria

O Radar ANP no MPFM nao altera documentos de origem. Qualquer escrita operacional deve ficar limitada a tabelas locais de decisao/proposta ate haver aprovacao humana explicita e escopo definido.
