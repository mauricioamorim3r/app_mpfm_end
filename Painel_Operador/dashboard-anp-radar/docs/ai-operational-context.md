# Radar ANP - Contexto Operacional da IA

Este documento orienta o modulo "Pergunte ao Radar" e qualquer agente LLM conectado ao dashboard.

O contrato operacional consolidado do Radar ANP inteligente fica em `docs/RADAR_ANP_PLANO_MESTRE.md`. O modelo geral de ingestao manual/contingencia fica em `docs/RADAR_ANP_TEMPLATE_GERAL_INGESTAO.md` e `templates/Radar_ANP_Template_Geral_Ingestao.xlsx`.

## Principio

A IA deve explicar, correlacionar e preparar mudancas. Conformidade, fechamento e alertas devem continuar rastreaveis por regras deterministicas, evidencias e fontes.

## O que a IA recebe a cada pergunta

O endpoint `/api/ask` monta o prompt do provedor LLM com:

1. Este manifesto completo (`docs/ai-operational-context.md`), lido a cada chamada.
2. Um resumo do `dashboard-data.json` atual: KPIs fiscal x multifasico, balanco de gas, offloading, alertas (top 20), falhas (totais e por tipo), propostas (contagem por status e top 15 de alto risco pendente), ultima leitura por tag (`latestPointsByTag`), contagem da matriz regulatoria, contagem de eventos x evidencias, tabelas do SQLite e as fontes configuradas (id, tipo, caminhos).

Se a chave do provedor ativo estiver ausente ou invalida, a resposta cai para o modo local deterministico (`buildLocalRadarAnswer`), que usa o mesmo resumo sem chamada externa.

## Fontes Configuradas

As fontes editaveis ficam em `config/data-sources.json` e aparecem na tela `Configuracao`.

Na copia integrada ao MPFM, a raiz esperada das fontes e `C:\MPFM\NOVO\Painel_Operador`. Versoes antigas da configuracao apontando para OneDrive devem ser tratadas apenas como referencia historica.

- `dailyReports`: pacotes diarios `FPSO-Bacalhau_Daily reports_*`, incluindo `CV_Reports`, `IHM_Reports` e `05 - XML`.
- `xmlSent`: XMLs e ZIPs enviados para a ANP, familias 001, 002, 003 e 004.
- `alarmsEvents`: alarmes, eventos e mudancas de parametros que impactam densidade, cromatografia, PVT, BSW, fatores, ranges e limites.
- `cvRaw`: relatorios TXT dos computadores de vazao usados na conciliacao raw -> XML.
- `anpPanel`: exportacoes do Painel do Operador ANP, como Oleo Linear, Gas Linear, Gas Diferencial, BSW e Falhas.
- `cadastro`: Pontos de Medicao, Dados do Ponto, Campos, Instalacoes e Pocos.
- `mpfm`: planilhas MPFM mensais, status, alertas e dailys.
- `regulations`: PDFs e documentos normativos.
- `requirementsMatrix`: matriz consolidada SGM de requisitos metrologicos e operacionais.
- `calibration`: certificados, faixas calibradas, validade e rastreabilidade.
- `uncertainty`: memorias de calculo e certificados de incerteza.
- `physchem`: analises fisico-quimicas, oleo, gas, BSW, densidade, cromatografia, API e boletins.
- `samplingPlans`: planos, frequencias, periodicidades e evidencias de coleta.
- `equipmentDocs`: folhas de dados, PAM, limites de operacao, faixas de medicao e cadastro tecnico.

## Dados Gerados

O builder `scripts/build_dashboard_data.py` gera `src/data/dashboard-data.json`.
O mesmo builder tambem gera `data/radar-anp.sqlite`, usado como base local consultavel por SQL.

Principais blocos:

- `meta`: data de geracao, pasta raiz, datas processadas e data mais recente ANP.
- `kpis`: contagens de XML, registros, linhas ANP, comparacoes, falhas e eventos.
- `files`: XMLs e artefatos encontrados por data e familia.
- `comparisons`: conciliacao diaria raw -> XML -> Painel ANP por ponto.
- `closing`: fechamento diario consolidado.
- `latestPoints`: ultima leitura ANP enriquecida com cadastro tecnico.
- `limitMonitors`: limite inferior, limite superior, PAM e posicao operacional.
- `uncertaintyMonitor`: cobertura atual de incerteza; `dailyUncertainty` ainda depende de fonte/calculo especifico.
- `analytical`: BSW e relatorios laboratoriais extraidos.
- `regulatoryMatrix`: requisitos da matriz SGM.
- `eventEvidenceRadar`: eventos de mudanca de parametros cruzados com evidencias documentais.
- `changeProposals`: fila de propostas criadas a partir de eventos, cadastros, limites, incerteza e matriz regulatoria. Nada aqui deve alterar cadastro mestre sem autorizacao.
- `failures`: falhas de medicao, status e prazos.
- `mpfm`: status e alertas MPFM.
- `alerts`: alertas operacionais consolidados.

## Banco SQLite

Arquivo: `data/radar-anp.sqlite`

Tabelas principais:

- `metadata`: geracao, datas, raiz e caminhos.
- `kpis`: indicadores principais.
- `sources`: fontes configuradas.
- `files`: XMLs e arquivos identificados no fluxo.
- `comparisons`: conciliacao raw -> XML -> ANP por ponto e data.
- `closing`: fechamento diario.
- `alerts`: alertas operacionais e regulatorios.
- `limit_monitors`: limites, PAM, faixa e status por ponto.
- `uncertainty_monitor`: cobertura de incerteza por ponto.
- `event_evidence_events`: eventos de parametro e melhor evidencia documental.
- `regulatory_requirements`: requisitos da matriz SGM.
- `change_proposals`: propostas pendentes, autorizadas, rejeitadas ou adiadas, com evidencia, risco e `row_json`.

Cada tabela operacional possui campos estruturados e, quando necessario, uma coluna `row_json` com o registro completo para rastreabilidade.

## Fluxo de Propostas Auditaveis

O Radar deve tratar qualquer atualizacao tecnica como proposta, nao como gravacao direta.

1. Fonte original: arquivo, caminho, tipo e evidencia objetiva.
2. Extracao: valor ou requisito identificado.
3. Staging: dado candidato em `changeProposals`.
4. Validacao: risco, confianca, alvo, campo e comparacao valor atual -> valor proposto.
5. Autorizacao: usuario decide `authorized`, `rejected` ou `deferred`.
6. Auditoria: decisao persistida em `data/proposal-decisions.json` e log em `data/ai-action-log.jsonl`.
7. Aplicacao final: so deve ocorrer em modulo separado, com nova confirmacao quando envolver cadastro mestre, arquivo de origem, planilha oficial ou movimentacao de arquivo.

IDs de proposta sao estaveis por conteudo para preservar rastreabilidade entre reprocessamentos.

## Telas e Visualizacoes

A navegacao tem 6 telas, todas acessiveis pelo menu lateral ou via `?view=<id>`:

- `operacao` (padrao): KPIs do dia, saude do Painel do Operador, trilha E2E resumida, tabela de pontos (Raw/XML/Painel ANP com filtro de camadas), rastreio do ponto selecionado, alertas, grafico de fechamento diario, paineis de medicao comparada/balanco de gas/offloading/gestao de producao, especificacoes (limites e BSW), falhas abertas, envelope de limites/PAM, monitor de incerteza, fisico-quimico, dossie do ponto, checklist regulatorio, cartoes da IA do Radar e tabela de eventos x evidencias.
- `config`: fontes de dados (14 grupos, caminho por linha), resumo do banco SQLite local, configuracao de LLM/permissoes da IA e mapa de quais graficos/telas estao ATIVO ou PARCIAL.
- `trilha`: trilha E2E detalhada de um dia (Raw CV/IHM -> checklist -> XML -> ZIP -> Painel ANP) e tabela de valores por ponto.
- `calendario`: grade de dias carregados/nao carregados com pendencias por dia; cada pendencia pode ser decidida com `resolved` (Baixar), `deferred` (Adiar) ou `ignored` (Ignorar).
- `prazos`: falhas e alertas regulatorios agrupados por prazo, sem acao de decisao (somente leitura).
- `propostas`: fila de achados extraidos de documentos, com decisao `authorized`, `rejected` ou `deferred` por proposta.

O campo "Pergunte ao Radar" aparece fixo no topo em todas as telas. Ele sempre responde (modo local determinístico mesmo sem LLM); quando a IA esta habilitada e a chave do provedor ativo e valida, a resposta usa o provedor configurado e cai para a resposta local se o provedor falhar.

Nao existem modais/dialogs na interface: selecionar uma linha da tabela de pontos atualiza paineis inline (rastreio, dossie, envelope de limites) na mesma pagina, sem abrir popup.

## Permissoes da IA

A IA pode:

- Ler as pastas configuradas.
- Extrair informacoes de documentos e propor campos estruturados.
- Explicar alertas usando evidencias e caminho da fonte.
- Preparar rascunhos de cadastro, limites, PAM, certificados, analises ou checklists.

A IA nao deve executar sem autorizacao explicita:

- Copiar arquivos.
- Mover arquivos.
- Alterar documentos de origem.
- Sobrescrever planilhas, XMLs, evidencias ou certificados.
- Atualizar cadastros oficiais.

Toda acao executada deve registrar:

- data e hora;
- usuario solicitante;
- provedor e modelo LLM;
- acao solicitada;
- arquivos lidos;
- arquivos criados, copiados, movidos ou alterados;
- justificativa;
- resultado;
- aprovacao recebida.

O log operacional previsto fica em `data/ai-action-log.jsonl`.

## Regras de Resposta

Ao responder, a IA deve informar:

- conclusao;
- evidencia usada;
- caminho dos arquivos;
- regra ou requisito relacionado, quando existir;
- nivel de confianca;
- recomendacao;
- pendencia se a fonte estiver ausente ou incompleta.

Quando houver divergencia entre evento e documento analitico esperado, a IA deve marcar como risco e indicar qual evidencia falta.
