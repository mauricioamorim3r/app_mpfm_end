# PRD - Plataforma Local de Inteligencia Operacional de Medicao Bacalhau

## 1. Resumo Executivo

A Plataforma Bacalhau e uma aplicacao local, offline-first, voltada para ingestao, organizacao tecnica, diagnostico, auditoria, baseline, comparacao de configuracao, analise de eventos e consolidacao operacional de medicao.

O produto nasce para transformar artefatos operacionais hoje dispersos em ZIP, TXT, PDF e exportacoes tecnicas em um repositorio auditavel e acionavel. Em vez de apenas abrir arquivos, a plataforma preserva o bruto, extrai metadados, normaliza registros, compara estados, identifica mudancas relevantes, reconstrui linhas do tempo e gera relatorios tecnicos e operacionais.

A estrategia de produto sera executada em camadas:

- `Release 1`: configuracao, eventos, diff, baseline e auditoria tecnicamente completos
- `Release 2`: relatorio diario, consolidacao operacional e suporte ao fechamento
- `Release 3`: historico leve, tendencias, drift e integridade metrologica
- `Release 4`: cockpit completo de medicao e apropriacao

## 2. Contexto

Os ativos de medicao do projeto Bacalhau geram e dependem de multiplos artefatos tecnicos:

- `Configuration-*.txt`
- `Events_Snapshot-*.txt`
- relatorios PDF/TXT
- logs exportados
- arquivos de tendencia e historico
- futuramente CSV, XML ANP e dumps de banco

Hoje esses artefatos sao usados principalmente como evidencia pontual ou consulta manual. Isso dificulta:

- manter baseline oficial por ativo
- provar o que mudou entre snapshots
- correlacionar eventos com intervencoes humanas
- investigar divergencias entre equipamentos redundantes
- construir historico tecnico reutilizavel
- alimentar relatorios diarios e rastreabilidade operacional

O ZIP analisado como referencia deste PRD confirma a oportunidade:

- dois snapshots de configuracao (`21JN101A` e `21JN101B`)
- dois snapshots de eventos
- diferencas claras entre ativos redundantes, como IP, tag, serial e parametros de pulso/override
- evidencias de eventos operacionalmente relevantes, como login, alteracao de densidade padrao e alarmes de `Run 2`

## 3. Visao do Produto

Criar uma plataforma local de inteligencia operacional de medicao capaz de:

- ingerir artefatos tecnicos heterogeneos
- estruturar configuracoes, eventos, alarmes, medicoes e evidencias
- operar sem dependencia de conectividade externa
- oferecer auditoria, diff, baseline e diagnostico orientados a medicao
- evoluir para um cockpit diario de fechamento e apropriacao

## 4. Problema a Resolver

### 4.1 Problemas Atuais

- Dependencia de leitura manual de relatorios e snapshots
- Dificuldade para comparar configuracoes de forma confiavel
- Ausencia de trilha de auditoria consolidada
- Baixa rastreabilidade entre arquivo original, valor extraido e conclusao tecnica
- Falta de visao historica para eventos recorrentes e degradacao operacional
- Esforco alto para gerar relatorios tecnicos com evidencias

### 4.2 Impacto de Negocio e Operacao

- aumento do tempo de resposta em investigacoes
- risco de perda de contexto tecnico
- dificuldade para suportar auditoria e MOC de medicao
- baixo reaproveitamento de dados para fechamento diario
- menor confianca em analises entre equipamentos A/B e sistemas redundantes

## 5. Objetivos

### 5.1 Objetivos de Produto

- Centralizar artefatos tecnicos de medicao em um repositorio local auditavel
- Permitir comparacao confiavel entre snapshots de configuracao
- Detectar e classificar mudancas com foco metrologico e operacional
- Estruturar eventos e alarmes em timeline pesquisavel
- Produzir relatorio tecnico automatico com evidencias
- Preparar a base para relatorio diario e consolidacao operacional

### 5.2 Objetivos de Usuario

- descobrir rapidamente o que mudou entre dois snapshots
- identificar eventos relevantes por ativo, run, severidade e janela de tempo
- manter baseline oficial por ativo ou estacao
- provar a origem de cada analise com hash e arquivo-fonte
- reduzir o tempo de montagem de pareceres tecnicos

### 5.3 Nao Objetivos Iniciais

- controle online em tempo real dos equipamentos
- substituicao de sistemas oficiais de supervisao
- integracao corporativa multiusuario na primeira fase
- automacao de escrita de configuracao de volta no equipamento

## 6. Usuarios-Alvo

### 6.1 Usuarios Primarios

- engenheiro de medicao
- especialista metrologico
- instrumentista senior
- tecnico de automacao e manutencao

### 6.2 Usuarios Secundarios

- coordenacao de operacao
- equipe de confiabilidade
- equipe de apropriacao e fechamento
- auditoria tecnica e compliance

## 7. Casos de Uso Prioritarios

1. Comparar dois arquivos de configuracao e listar mudancas relevantes
2. Verificar se ativos redundantes A/B estao realmente sincronizados
3. Identificar alteracoes metrologicas, como densidade, K-factor, range e overrides
4. Ler eventos do dia e reconstruir a linha do tempo do incidente
5. Detectar eventos recorrentes, chattering e janelas de intervencao humana
6. Manter um baseline oficial por ativo e validar novos snapshots contra ele
7. Gerar um relatorio tecnico pronto para envio com evidencias rastreaveis
8. Evoluir a mesma base para alimentar o relatorio diario do Bacalhau

## 8. Proposta de Valor

### 8.1 Valor Imediato

- diff tecnico confiavel
- auditoria objetiva
- diagnostico mais rapido
- suporte a investigacao de falhas
- base concreta para MOC tecnico de medicao

### 8.2 Valor Estrategico

- historico operacional estruturado
- base unificada para configuracao, eventos e relatorios
- menor dependencia de analise manual
- ponte natural para cockpit diario, KPI e apropriacao

## 9. Estrategia de Releases

### 9.1 Release 1 - SGMed Inspector Completo

Escopo prioritario e profundo em configuracao, eventos, diff e auditoria.

### Entregas Principais

- ingestao de `ZIP`, `TXT` e `PDF`
- inventario automatico do conteudo ingerido
- identificacao do tipo de arquivo
- parser de `Configuration-*`
- parser de `Events_Snapshot-*`
- persistencia de bruto + tratado + hash + origem
- cadastro de ativos, FCs, runs, TAGs, versoes e rede
- baseline oficial por ativo
- comparacao A x B, antes x depois e contra baseline
- classificacao de mudancas
- timeline de eventos
- agrupamento por ativo, run, severidade, causa provavel e categoria
- deteccao de padroes recorrentes
- geracao de relatorio tecnico automatico

### Resultado Esperado

Ao final da Release 1, o usuario consegue abrir um ZIP como o analisado, identificar que `21JN101A` e `21JN101B` diferem em IP, tag, serial e parametros de pulso/override, correlacionar isso com eventos como alteracao de densidade ou alarmes de `Run 2` e exportar um relatorio tecnico com evidencias.

### 9.2 Release 2 - Consolidacao Operacional e Relatorio Diario

Escopo completo de relatorio diario e consolidacao operacional.

### Entregas Principais

- ingestao de relatorios diarios `PDF/TXT`
- extracao de variaveis mono e multifasicas
- consolidacao por periodo e por ativo
- bloco de status do sistema
- bloco de alarmes e acoes
- bloco de baseline e rastreabilidade de mudancas
- geracao de relatorio diario corporativo
- exportacao para `PDF`, `Word` e `Markdown`

### Resultado Esperado

Ao final da Release 2, a plataforma passa a suportar a consolidacao diaria do Bacalhau e a reunir configuracao, eventos, status do sistema e evidencias em um relatorio operacional consistente.

### 9.3 Release 3 - Historico Leve e Integridade Metrologica

- importacao de trend export e historicos tabulares
- construcao de series temporais
- comparacao `D` x `D-1`
- deteccao de drift, gaps e comportamento anomalo
- health score por medidor
- verificacao de coerencia entre configuracao e processo

### 9.4 Release 4 - Cockpit Completo Bacalhau

- integracao de monofasico e multifasico
- consolidacao topside, subsea e separador de teste
- XML ANP
- balanco de massa
- apropriacao
- historico de acoes manuais
- cockpit gerencial e operacional unificado

## 10. Requisitos Funcionais

### 10.1 Ingestao

- permitir arrastar e soltar arquivos e ZIPs
- permitir apontar uma pasta para ingestao em lote
- descompactar ZIP localmente
- inventariar todos os arquivos encontrados
- detectar tipo do arquivo por nome, padrao e conteudo
- registrar data de ingestao, usuario local, origem e hash

### 10.2 Parsing e Normalizacao

- extrair campos estruturados de configuracao
- extrair eventos, alarmes, severidade, usuario, IP e horario
- mapear ativos, FCs, runs, TAGs, modulos, versoes e rede
- normalizar unidades, nomes e categorias
- manter ligacao entre valor extraido e trecho de evidencia
- versionar parser e regras aplicadas

### 10.3 Repositorio Tecnico

- armazenar o arquivo bruto original
- armazenar o registro tratado
- permitir busca por ativo, data, tipo de artefato e tag
- manter baseline oficial e historico de baselines

### 10.4 Diff e Gestao de Mudanca

- comparar dois snapshots quaisquer
- comparar snapshot contra baseline
- destacar insercoes, remocoes e alteracoes
- classificar mudancas em:
  - critica
  - metrologica
  - operacional
  - rede/comunicacao
  - cosmetica
- permitir comentario tecnico e aprovacao manual do diff

### 10.5 Eventos e Diagnostico

- listar eventos por janela de tempo
- filtrar por ativo, run, severidade, categoria e usuario
- detectar padroes recorrentes e chattering
- identificar login, logout, alteracao de parametro e alarmes relevantes
- montar timeline de incidente
- sugerir diagnostico provavel baseado em regras

### 10.6 Relatorio Tecnico

- gerar resumo executivo
- listar achados criticos e importantes
- anexar evidencias por arquivo e trecho
- registrar riscos e recomendacoes
- exportar em `PDF`, `Word` e `Markdown`

### 10.7 Relatorio Diario

- consolidar dados de relatorios diarios e artefatos tecnicos
- gerar secoes de status do sistema, alarmes, acoes e riscos
- manter historico de relatorios diarios gerados

## 11. Requisitos Nao Funcionais

### 11.1 Arquitetura

- operar localmente em notebook ou estacao de engenharia
- funcionar offline
- ter instalacao simples
- nao depender de servicos externos para a funcao principal

### 11.2 Auditoria e Rastreabilidade

- cada conclusao precisa apontar para sua evidencia
- cada arquivo precisa ter hash e origem
- cada valor extraido precisa informar parser e versao
- toda classificacao automatica precisa ser explicavel

### 11.3 Performance

- ingestao de ZIP de tamanho tipico em poucos segundos
- abertura de diff de snapshots sem reprocessamento completo
- filtros e timelines com resposta interativa em volume de estacao

### 11.4 Seguranca

- dados armazenados apenas localmente por padrao
- trilha de auditoria de acoes do usuario
- permissao para exportacao controlada
- opcao futura de criptografia do banco local

### 11.5 Manutenibilidade

- parser modular por tipo de arquivo
- regras de negocio desacopladas do parser
- banco simples de migrar e versionar
- testes automatizados para parsers e classificadores

## 12. UX e Modulos de Interface

### 12.1 Aba Ingestao

- upload de ZIP, TXT e PDF
- inventario do que entrou
- tipo de arquivo detectado
- status do parsing
- erros e alertas de ingestao

### 12.2 Aba Ativos e Configuracao

- lista de FCs, runs, TAGs e instrumentos
- versoes de software e hardware
- IP, rede e modulos
- parametros metrologicos principais
- baseline oficial por ativo

### 12.3 Aba Diff e Gestao de Mudanca

- comparacao lado a lado
- destaque visual para alteracoes
- classificacao por severidade e impacto
- comparacao A/B e antes/depois
- geracao de parecer tecnico

### 12.4 Aba Eventos e Diagnostico

- timeline
- top eventos do dia
- eventos recorrentes por run
- janela de intervencao humana
- sugestao de diagnostico

### 12.5 Aba Relatorio Tecnico

- resumo executivo
- achados
- evidencias
- riscos
- recomendacoes
- exportacoes

### 12.6 Modulos Futuramente Integrados

- relatorio diario
- historico e tendencia
- KPI de integridade
- apropriacao e balanco

## 13. Arquitetura Tecnica Recomendada

### 13.1 Stack

- `Python + FastAPI` no backend local
- `SQLite` como banco principal local
- `React + Vite` no frontend local
- engine de parser por tipo de arquivo
- engine de regras para QA, diff e diagnostico

### 13.2 Componentes

#### 13.2.1 Ingestion Service

Responsavel por receber arquivos, descompactar ZIP, calcular hash, registrar evidencia e encaminhar artefatos para parsing.

#### 13.2.2 Parser Registry

Responsavel por selecionar o parser correto para cada tipo de artefato e aplicar versao de parser apropriada.

#### 13.2.3 Normalization Layer

Responsavel por converter dados extraidos em modelos internos consistentes, preservando referencia ao original.

#### 13.2.4 Evidence Store

Responsavel por manter bruto, hash, metadados e ligacao com entidades tratadas.

#### 13.2.5 Configuration Analyzer

Responsavel por baseline, diff, classificacao de mudancas e comparacao A/B.

#### 13.2.6 Event Intelligence Engine

Responsavel por timeline, agregacoes, recorrencia, chattering e diagnostico inicial.

#### 13.2.7 Report Engine

Responsavel por montar relatorios tecnicos e, depois, relatorios diarios.

## 14. Modelo de Dados Inicial

Tabelas principais:

- `files_raw`
- `ingestion_batches`
- `parsed_records`
- `assets`
- `asset_components`
- `config_snapshots`
- `config_parameters`
- `config_diffs`
- `events`
- `alarms`
- `measurements`
- `qa_flags`
- `actions_log`
- `baselines`
- `daily_reports`

### 14.1 Regra de Ouro de Persistencia

Para cada dado relevante, a plataforma deve manter:

- bruto original
- valor extraido
- valor normalizado
- regra aplicada
- evidencia
- timestamp
- versao do parser

## 15. Regras de Classificacao Inicial

### 15.1 Mudancas Metrologicas

- densidade padrao
- K-factor
- fator de calibracao
- range de processo
- modo de pulso
- overrides de produto ou processo

### 15.2 Mudancas Operacionais

- habilitacao/desabilitacao de funcoes
- alteracoes de alarmes
- parametros de run
- comportamentos de fallback

### 15.3 Mudancas de Rede e Comunicacao

- IP
- gateway
- subnet
- configuracao de porta
- parametros de comunicacao serial

### 15.4 Mudancas Cosmeticas

- descricao
- rotulos
- campos informativos sem impacto operacional ou metrologico

## 16. Exemplo de Valor com o ZIP de Referencia

Com os artefatos analisados neste PRD, a plataforma deve ser capaz de:

- identificar que `21JN101A` e `21JN101B` sao ativos distintos e potencialmente redundantes
- destacar diferencas de `IP address 1` e `IP address 2`
- destacar diferencas de `Serial nr.`, `Flow computer tag` e `Tag`
- detectar diferencas em `Pulse single / dual` e `Override`
- registrar eventos de login/logout do usuario `administrator`
- capturar a alteracao de `standard density override` de `854.9` para `854.4`
- destacar alarmes recorrentes em `Run 2`, como `Pulse input failure`, `No B pulses` e `Flow rate alarm Low Low`
- gerar um relatorio dizendo o que mudou, quando ocorreu e qual o impacto potencial

## 17. Sucesso do Produto

### 17.1 Indicadores da Release 1

- tempo para ingestao completa de um ZIP tecnico
- tempo para localizar um ativo e abrir seu baseline
- tempo para comparar dois snapshots
- percentual de parametros relevantes extraidos corretamente
- percentual de eventos corretamente categorizados
- tempo para gerar um relatorio tecnico

### 17.2 Indicadores da Release 2

- tempo para consolidar relatorio diario
- percentual de campos diarios preenchidos automaticamente
- reducao do retrabalho manual na elaboracao do relatorio

## 18. Riscos

- alta variabilidade de layout entre exportacoes reais
- nomenclatura inconsistente entre ativos e documentos
- classificacao incorreta de impacto sem calibracao de regras
- tentacao de expandir escopo antes de fechar a Release 1
- dependencia excessiva de heuristicas sem evidencia clara

## 19. Mitigacoes

- parser versionado por layout e tipo de arquivo
- testes com biblioteca de artefatos reais anonimizados
- trilha de explicabilidade para toda classificacao automatica
- priorizacao forte da Release 1 antes da consolidacao diaria
- interface que sempre mostre o original e o tratado lado a lado

## 20. Roadmap de Implementacao Recomendado

### Fase 1

- leitor
- parser
- banco local
- baseline
- diff
- eventos

### Fase 2

- dashboard de integridade
- relatorio tecnico automatico
- exportacoes

### Fase 3

- ingestao dos relatorios diarios Bacalhau
- consolidacao operacional
- relatorio diario corporativo

### Fase 4

- historico, tendencia e KPI
- apropriacao
- XML ANP
- cockpit completo

## 21. Decisoes Fechadas Neste PRD

- o produto sera uma `plataforma completa Bacalhau`, nao apenas um leitor isolado
- a arquitetura base sera `local/offline-first`
- a `Release 1` sera completa em configuracao, eventos, diff e auditoria
- a `Release 2` vira em seguida, completa em relatorio diario e consolidacao operacional

## 22. Proxima Etapa Recomendada

Quebrar a `Release 1` em um plano de implementacao com epicos, historias, modelo de banco inicial, contratos de parser e backlog tecnico do `SGMed Inspector`.
