# Plano de Implementacao - Release 1 do SGMed Inspector

## 1. Objetivo

Este plano detalha a implementacao da `Release 1` da Plataforma Bacalhau, correspondente ao `SGMed Inspector` completo em:

- ingestao local de artefatos tecnicos
- parsing de configuracao e eventos
- repositorio auditavel de evidencias
- baseline por ativo
- comparacao de snapshots
- classificacao de mudancas
- timeline e inteligencia inicial de eventos
- relatorio tecnico automatico

O foco desta release e resolver profundamente o dominio de `configuracao + eventos + diff + auditoria` antes da expansao para relatorio diario e consolidacao operacional.

## 2. Escopo Fechado da Release 1

### 2.1 Dentro do Escopo

- upload local de `ZIP`, `TXT` e `PDF`
- descompactacao de ZIP
- inventario de arquivos ingeridos
- persistencia do bruto com hash
- parser de `Configuration-*.txt`
- parser de `Events_Snapshot-*.txt`
- modelo de ativos e snapshots
- baseline oficial por ativo
- comparacao `A x B`, `antes x depois` e `snapshot x baseline`
- classificacao de mudancas por categoria e criticidade
- timeline de eventos
- filtros por ativo, run, usuario, severidade, categoria e janela
- deteccao de recorrencia e chattering
- relatorio tecnico exportavel em `Markdown`

### 2.2 Fora do Escopo

- escrita de configuracao de volta ao equipamento
- integracao online com FCs
- consolidacao diaria completa
- tendencias historicas
- XML ANP
- apropriacao
- multiusuario corporativo
- sincronizacao em nuvem

## 3. Resultado de Negocio Esperado

Ao fim da release, um usuario deve conseguir:

1. importar um ZIP tecnico local
2. visualizar quais arquivos foram encontrados e classificados
3. abrir os dados estruturados de um ativo
4. definir ou atualizar um baseline oficial
5. comparar snapshots e ver alteracoes destacadas
6. entender a criticidade e o impacto potencial de cada mudanca
7. consultar eventos e correlaciona-los com intervencoes ou alarmes
8. gerar um relatorio tecnico com evidencias

## 4. Arquitetura da Release 1

### 4.1 Stack

- backend local: `Python 3.12 + FastAPI`
- frontend local: `React + Vite + TypeScript`
- persistencia: `SQLite`
- ORM recomendado: `SQLAlchemy`
- validacao de modelos: `Pydantic`
- parser engine: modulos Python por tipo de artefato
- exportacao inicial: `Markdown`

### 4.2 Estrutura Logica

- `frontend`
  - ingestao
  - ativos
  - diff
  - eventos
  - relatorio
- `backend/api`
  - endpoints REST locais
- `backend/services`
  - ingestao
  - parsing
  - baseline
  - diff
  - eventos
  - relatorios
- `backend/domain`
  - entidades e regras de negocio
- `backend/parsers`
  - parser de configuracao
  - parser de eventos
- `backend/storage`
  - SQLite
  - armazenamento de evidencias

### 4.3 Principios de Implementacao

- parser desacoplado de regras de classificacao
- evidencia sempre ligada ao valor interpretado
- schema interno estavel, parser externo versionado
- Release 1 otimizada para auditabilidade, nao para complexidade visual

## 5. Milestones

### 5.1 M0 - Fundacao Tecnica

Objetivo: deixar o projeto executavel localmente com espinha dorsal pronta.

Entregas:

- scaffold do backend local
- scaffold do frontend local
- estrutura de diretorios
- configuracao basica de banco SQLite
- migracao inicial
- modelo de armazenamento de arquivos brutos
- fluxo minimo de healthcheck e inicializacao

Critério de pronto:

- app sobe localmente
- banco e criado automaticamente
- arquivo local pode ser registrado com hash

### 5.2 M1 - Ingestao e Inventario

Objetivo: aceitar ZIP/TXT/PDF e inventariar o conteudo com rastreabilidade.

Entregas:

- upload de arquivo
- upload de ZIP
- descompactacao local
- identificacao do tipo de artefato
- tabela de lotes de ingestao
- tabela de arquivos brutos
- UI de inventario

Critério de pronto:

- um ZIP como o de referencia aparece como lote
- cada arquivo do lote tem hash, tipo detectado e status

### 5.3 M2 - Parsers de Configuracao e Eventos

Objetivo: transformar `Configuration-*` e `Events_Snapshot-*` em dados estruturados.

Entregas:

- parser de configuracao
- parser de eventos
- persistencia em tabelas normalizadas
- modelos de ativo, snapshot e evento
- vinculacao entre evidencias e registros estruturados

Critério de pronto:

- dados de `21JN101A` e `21JN101B` ficam consultaveis por API e UI
- alteracao de densidade e alarmes de `Run 2` sao representados como eventos estruturados

### 5.4 M3 - Ativos, Baseline e Diff

Objetivo: permitir leitura operacional dos snapshots e comparacao confiavel.

Entregas:

- tela de ativos
- tela de snapshot
- definicao de baseline oficial
- comparacao snapshot x snapshot
- comparacao snapshot x baseline
- classificador de mudancas

Critério de pronto:

- usuario consegue comparar `21JN101A` e `21JN101B`
- diferencas como IP, tag, serial, pulso e override aparecem classificadas

### 5.5 M4 - Eventos e Diagnostico Inicial

Objetivo: transformar export de eventos em timeline util para investigacao.

Entregas:

- tela de timeline
- filtros por ativo, run, usuario, categoria e periodo
- agrupamentos e contagens
- deteccao de recorrencia
- deteccao de chattering
- primeira camada de sugestao de diagnostico

Critério de pronto:

- usuario enxerga a sequencia de login, alteracao de parametro e alarmes
- sistema identifica padrao recorrente de `Pulse input failure` e `No B pulses`

### 5.6 M5 - Relatorio Tecnico

Objetivo: fechar o ciclo com saida pronta para analise e envio.

Entregas:

- geracao de resumo executivo
- achados criticos e importantes
- bloco de evidencias
- bloco de riscos e recomendacoes
- exportacao em `Markdown`

Critério de pronto:

- relatorio tecnico pode ser gerado para um lote ou comparacao

## 6. Epicos e Backlog

### 6.1 Epico A - Fundacao do Produto

Historias:

- como desenvolvedor, quero subir backend e frontend localmente para iniciar o produto
- como sistema, quero criar o banco automaticamente para reduzir friccao
- como sistema, quero manter configuracoes locais de ambiente para operacao offline

Tarefas tecnicas:

- criar estrutura `backend/` e `frontend/`
- configurar FastAPI
- configurar Vite + React + TypeScript
- definir pasta de dados local
- definir mecanismo de migracao
- configurar logging estruturado local

### 6.2 Epico B - Ingestao e Evidencia

Historias:

- como usuario, quero importar um ZIP tecnico
- como usuario, quero ver os arquivos extraidos
- como auditor, quero hash e origem de cada arquivo

Tarefas tecnicas:

- implementar endpoint de upload
- implementar servico de descompactacao
- detectar MIME e tipo logico do arquivo
- calcular `sha256`
- persistir lote, arquivo e metadados
- copiar bruto para storage local gerenciado

### 6.3 Epico C - Parser de Configuracao

Historias:

- como engenheiro, quero ler snapshots de configuracao de forma estruturada
- como usuario, quero localizar FC, tag, versao, IP e parametros chave

Tarefas tecnicas:

- mapear secoes do relatorio
- extrair cabecalho, device info, versions, network, ports e meter data
- normalizar pares `chave -> valor`
- separar metadados do ativo dos parametros de configuracao
- armazenar trecho original de evidencia por campo relevante

### 6.4 Epico D - Parser de Eventos

Historias:

- como usuario, quero ver eventos estruturados por horario
- como analista, quero saber usuario, origem, run e tipo do evento

Tarefas tecnicas:

- extrair cabecalho do relatorio de eventos
- converter linhas em eventos estruturados
- classificar tipos como login, logout, parametro alterado, alarme e comando
- extrair valores anterior e novo quando presentes
- identificar `run` e objeto afetado

### 6.5 Epico E - Modelo de Ativos

Historias:

- como usuario, quero ver todos os FCs e snapshots associados
- como usuario, quero navegar por ativo e por lote

Tarefas tecnicas:

- criar entidade de ativo
- vincular snapshot a ativo
- consolidar aliases de tags e nomes
- expor visao de ativos na API

### 6.6 Epico F - Baseline e Diff

Historias:

- como engenheiro, quero escolher um baseline oficial
- como usuario, quero comparar snapshots e ver o que mudou
- como auditor, quero separar mudancas metrologicas de cosmeticas

Tarefas tecnicas:

- definir estrategia de comparacao baseada em parametros normalizados
- construir diff deterministico
- implementar classificador inicial por regras
- marcar mudancas com criticidade
- permitir promocao de snapshot a baseline

### 6.7 Epico G - Eventos e Diagnostico

Historias:

- como usuario, quero uma timeline filtravel
- como analista, quero ver eventos recorrentes e suspeitas de falha

Tarefas tecnicas:

- criar agregacoes por ativo e run
- detectar repeticao em janela curta
- detectar chattering por ida e volta rapida
- produzir sugestoes iniciais baseadas em regras

### 6.8 Epico H - Relatorio Tecnico

Historias:

- como usuario, quero gerar um relatorio tecnico com o diff e os eventos relacionados
- como gestor tecnico, quero um resumo executivo rapido

Tarefas tecnicas:

- montar template de relatorio em Markdown
- incluir evidencias, achados, riscos e recomendacoes
- permitir gerar relatorio por comparacao ou por lote

## 7. Modelo de Banco Inicial

### 7.1 Tabelas Minimas da Release 1

### `ingestion_batches`

- `id`
- `source_name`
- `created_at`
- `notes`

### `files_raw`

- `id`
- `batch_id`
- `original_name`
- `stored_path`
- `detected_type`
- `sha256`
- `size_bytes`
- `ingested_at`

### `assets`

- `id`
- `asset_key`
- `flow_computer_tag`
- `system_tag`
- `location`
- `company`
- `description`
- `last_seen_at`

### `config_snapshots`

- `id`
- `asset_id`
- `file_id`
- `snapshot_at`
- `device_name`
- `device_type`
- `application_version`
- `serial_number`
- `ip_address_1`
- `ip_address_2`
- `parser_version`

### `config_parameters`

- `id`
- `snapshot_id`
- `section`
- `parameter_key`
- `parameter_label`
- `normalized_value`
- `raw_value`
- `unit`
- `evidence_excerpt`

### `baselines`

- `id`
- `asset_id`
- `snapshot_id`
- `status`
- `selected_at`
- `selected_by`

### `config_diffs`

- `id`
- `left_snapshot_id`
- `right_snapshot_id`
- `parameter_key`
- `left_value`
- `right_value`
- `change_type`
- `category`
- `severity`
- `impact_summary`

### `events`

- `id`
- `asset_id`
- `file_id`
- `occurred_at`
- `run_number`
- `event_type`
- `category`
- `severity`
- `actor`
- `source_ip`
- `message`
- `old_value`
- `new_value`
- `evidence_excerpt`

### `qa_flags`

- `id`
- `related_entity_type`
- `related_entity_id`
- `flag_type`
- `severity`
- `message`
- `created_at`

### `report_exports`

- `id`
- `scope_type`
- `scope_id`
- `format`
- `file_path`
- `created_at`

### 7.2 Chaves de Correlacao

As correlacoes principais da release serao:

- `asset_id` como ancora operacional
- `file_id` como ancora de evidencia
- `snapshot_id` como ancora de configuracao
- `occurred_at` como ancora temporal

## 8. Contratos dos Parsers

### 8.1 Contrato Base

Todo parser deve retornar:

- `parser_name`
- `parser_version`
- `document_type`
- `source_file_id`
- `source_hash`
- `metadata`
- `records`
- `warnings`

### 8.2 Contrato do Parser de Configuracao

### Entrada

- arquivo TXT de configuracao, extraido ou standalone

### Saida

- metadados do documento
- identidade do ativo
- snapshot timestamp
- lista de secoes
- lista de parametros normalizados

### Exemplo de estrutura

```json
{
  "document_type": "configuration_report",
  "metadata": {
    "snapshot_at": "2026-03-29T05:48:01",
    "device_name": "21JN101A",
    "device_type": "Flow-X/C"
  },
  "asset": {
    "flow_computer_tag": "21JN101A",
    "system_tag": "20JX101",
    "location": "Sales Oil Skid"
  },
  "parameters": [
    {
      "section": "NETWORK SETTINGS",
      "parameter_key": "network.ip_address_1",
      "parameter_label": "IP address 1",
      "raw_value": "10.0.1.1",
      "normalized_value": "10.0.1.1",
      "evidence_excerpt": "IP address 1 10.0.1.1"
    }
  ]
}
```

### 8.3 Contrato do Parser de Eventos

### Entrada

- arquivo TXT de eventos, extraido ou standalone

### Saida

- metadados do documento
- identidade do ativo
- janela do relatorio
- lista de eventos estruturados

### Exemplo de estrutura

```json
{
  "document_type": "events_snapshot",
  "metadata": {
    "start_at": "2026-03-29T00:00:00",
    "end_at": "2026-03-29T05:47:39",
    "flow_computer_tag": "21JN101A"
  },
  "events": [
    {
      "occurred_at": "2026-03-29T05:46:54",
      "event_type": "parameter_changed",
      "category": "metrological",
      "severity": "important",
      "actor": "CommDrivers (10000)",
      "message": "Parameter Product 1 standard density override was changed from 854.9 to 854.4 by CommDrivers (10000)",
      "old_value": "854.9",
      "new_value": "854.4",
      "run_number": null
    }
  ]
}
```

## 9. Regras Iniciais de Classificacao

### 9.1 Severidade de Diff

- `critical`: impacto direto potencial na medicao ou coerencia do sistema
- `high`: impacto operacional relevante ou alteracao de configuracao sensivel
- `medium`: impacto indireto ou dependente de contexto
- `low`: cosmetico ou informativo

### 9.2 Categorias de Mudanca

- `metrological`
- `operational`
- `network`
- `cosmetic`

### 9.3 Regras Iniciais

- `standard density`, `K-factor`, `override`, `pulse mode` -> `metrological`
- `IP`, `gateway`, `com port` -> `network`
- alarmes e estados de run -> `operational`
- descricoes e labels sem impacto -> `cosmetic`

## 10. API Local Inicial

### 10.1 Ingestao

- `POST /api/ingestion/batches`
- `GET /api/ingestion/batches`
- `GET /api/ingestion/batches/{id}`

### 10.2 Ativos e Snapshots

- `GET /api/assets`
- `GET /api/assets/{id}`
- `GET /api/assets/{id}/snapshots`
- `POST /api/assets/{id}/baseline`

### 10.3 Diff

- `POST /api/diffs`
- `GET /api/diffs/{id}`

### 10.4 Eventos

- `GET /api/events`
- `GET /api/assets/{id}/events`

### 10.5 Relatorios

- `POST /api/reports/technical`
- `GET /api/reports/exports/{id}`

## 11. UI Inicial

### 11.1 Navegacao

- Ingestao
- Ativos
- Diff
- Eventos
- Relatorio

### 11.2 Tela de Ingestao

- arrastar e soltar
- lote recente
- arquivos do lote
- status de parsing
- alertas e warnings

### 11.3 Tela de Ativos

- lista de ativos
- resumo tecnico
- snapshots encontrados
- baseline atual

### 11.4 Tela de Diff

- seletor de snapshots
- lista de mudancas
- filtros por categoria e severidade
- destaque de valor anterior e novo

### 11.5 Tela de Eventos

- timeline
- filtro por periodo
- filtro por run
- filtro por tipo
- indicadores de recorrencia

### 11.6 Tela de Relatorio

- preview do relatorio
- exportacao em Markdown

## 12. Estrategia de Testes

### 12.1 Testes de Parser

- fixture com `Configuration-1.20260329054802.txt`
- fixture com `Configuration-1.20260329054843.txt`
- fixture com `Events_Snapshot-1.20260329054739.txt`
- fixture com `Events_Snapshot-1.20260329054829.txt`
- validacao de campos obrigatorios
- validacao de quantidade de eventos lidos

### 12.2 Testes de Diff

- deteccao correta de IP diferente
- deteccao correta de serial diferente
- deteccao correta de tag diferente
- deteccao correta de mudanca de `Pulse single / dual`
- deteccao correta de `Override`

### 12.3 Testes de Regras

- classificacao de densidade como `metrological`
- classificacao de IP como `network`
- classificacao de labels como `cosmetic`
- deteccao de chattering em eventos de ida e volta

### 12.4 Testes de Fluxo

- ingestao de ZIP completo
- comparacao de snapshots
- geracao de relatorio tecnico

## 13. Riscos Tecnicos da Release 1

- variacao real do layout dos relatorios
- dificuldade de consolidar `parameter_key` de modo consistente
- correlacao imperfeita de ativos entre arquivos com nomenclaturas diferentes
- excesso de heuristica na sugestao de diagnostico

## 14. Decisoes de Design Para Evitar Retrabalho

- manter `parameter_key` interno estavel desde o inicio
- tratar parser e classificador como camadas separadas
- guardar `evidence_excerpt` por registro relevante
- exportacao inicial apenas em Markdown para simplificar a release
- nao tentar cobrir todos os tipos de artefato na Release 1

## 15. Sequencia Recomendada de Execucao

1. fundacao tecnica
2. ingestao e evidencia
3. parser de configuracao
4. parser de eventos
5. ativos e baseline
6. diff e classificacao
7. timeline e diagnostico inicial
8. relatorio tecnico
9. testes de regressao e endurecimento

## 16. Definicao de Pronto da Release 1

A Release 1 esta pronta quando:

- o ZIP de referencia e importado com sucesso
- todos os arquivos sao inventariados e preservados com hash
- `21JN101A` e `21JN101B` aparecem como ativos consultaveis
- os snapshots de configuracao sao comparaveis
- as principais diferencas sao classificadas
- os eventos sao navegaveis em timeline
- a alteracao de densidade e os alarmes de `Run 2` sao detectados
- um relatorio tecnico em Markdown pode ser exportado

## 17. Proximo Passo Apos Este Plano

Quebrar cada milestone em tarefas de implementacao concretas e, se voce quiser, iniciar o scaffold do projeto com:

- backend FastAPI
- frontend React + Vite
- SQLite
- primeiras migracoes
- estrutura inicial de parser
