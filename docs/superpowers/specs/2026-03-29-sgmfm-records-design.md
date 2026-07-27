# Registros do SGM-FM - Design

Data: 2026-03-29

## 1. Objetivo

Adicionar um novo módulo na aplicação chamado `Registros do SGM-FM` para permitir cadastro, edição, consulta, geração em HTML e exportação opcional em PDF de três tipos de registros operacionais:

- `Rotina Diária MPFM Offshore`
- `Logbook de Documentos`
- `Análise PVT`

O módulo deve aproveitar a base principal já existente para sugerir e automatizar o preenchimento de campos como banco, TAG, instrumento, cobertura, desvios e outros dados operacionais já persistidos.

## 2. Escopo da primeira entrega

Entram nesta fase:

- novo item na sidebar: `Registros do SGM-FM`
- página própria com resumo dos 3 tipos de registro
- CRUD completo dos 3 formulários
- persistência em tabelas próprias no mesmo SQLite da aplicação
- geração oficial do registro em `HTML`
- exportação para `PDF` sob demanda
- automação de pré-preenchimento puxando dados da base principal
- configuração de visibilidade de campos por tipo de registro

Ficam para fase posterior:

- anexos binários/documentos
- versionamento formal por revisão
- assinaturas/aprovação eletrônica
- ordenação personalizada de campos pelo usuário
- autosave contínuo

## 3. Modelo operacional

### 3.1 Rotina Diária

Regra principal:

- `1 registro = 1 data_base + 1 ponto_de_medicao`

Consequências:

- pode existir mais de um registro no mesmo dia, desde que para pontos diferentes
- se o dia estiver totalmente ok para um ponto, pode não existir registro

Exemplo:

- `2026-03-29 + PE_2`
- `2026-03-29 + Riser P2`

### 3.2 Logbook

- múltiplos registros sob demanda
- sem unicidade forte por dia
- voltado a fatos, documentos, decisões e rastreabilidade operacional

### 3.3 Análise PVT

- múltiplos registros sob demanda
- vinculados ao contexto técnico analisado
- o resultado da análise fica validado segundo o próprio registro salvo

## 4. Arquitetura

### 4.1 Backend

Novos componentes:

- `routes/sgmfm_routes.py`
- `repositories/sgmfm/sgmfm_repository.py`
- `services/sgmfm/sgmfm_service.py`
- `services/sgmfm/sgmfm_render_service.py`

Responsabilidades:

- repositório: CRUD, listagem, filtros, preferências de visibilidade
- serviço: pré-preenchimento a partir da base operacional e regras de negócio
- render: geração do HTML oficial e exportação PDF
- rota: APIs da nova tela

### 4.2 Frontend

Novos componentes:

- nova página em `index.html`
- `static/app.sgmfm.js`
- estilos complementares em `static/app.layout.css`

O módulo deve seguir os padrões atuais da aplicação e respeitar `dark/light mode`.

## 5. Modelo de dados

Estratégia recomendada: tabelas separadas por tipo, para facilitar consulta, evolução e manutenção.

### 5.1 Tabelas

- `sgmfm_rotina_diaria`
- `sgmfm_logbook`
- `sgmfm_analise_pvt`
- `sgmfm_visibility_prefs`

### 5.2 Chaves

#### Rotina Diária

Chave lógica:

- `base_date + measurement_point`

#### Logbook

Chave:

- `id`

#### Análise PVT

Chave:

- `id`

Com campos de contexto para data, banco, TAG, instrumento, tipo e status.

## 6. Automação de pré-preenchimento

Ao abrir um novo registro, a aplicação deve consultar a base principal e sugerir campos como:

- banco
- loop
- tipo do medidor (`Subsea`/`Topside`)
- TAG/ponto
- instrumento associado
- cobertura `daily/hourly`
- presença/ausência de reconciliação
- desvios calculados
- observações do monitoramento
- cadastro mestre do ponto

### 6.1 Fontes principais

- `measurements_curated`
- `mpfm_monitoring_daily`
- `validation_issues`
- `pvt_params`
- `recon_runs`
- `cadastro.json`

## 7. Layout da nova tela

Novo item na sidebar:

- `Registros do SGM-FM`

### 7.1 Estrutura da página

- cards de resumo no topo:
  - rotinas do dia
  - logbooks recentes
  - análises PVT recentes
- navegação interna por seções ou abas:
  - `Rotina Diária`
  - `Logbook`
  - `Análise PVT`

Cada seção terá:

- filtros
- lista de registros
- botão `Novo`
- ações de `Abrir`, `Editar`, `Duplicar`, `Excluir`
- `Gerar HTML`
- `Exportar PDF`

## 8. Configuração de campos visíveis

Deve existir um botão na própria área `Registros do SGM-FM`:

- `Configurar campos`

As preferências serão salvas por tipo de registro:

- `Rotina Diária`
- `Logbook`
- `Análise PVT`

O objetivo é permitir:

- ocultar campos pouco usados
- simplificar o preenchimento operacional
- manter os formulários completos sem obrigar todos os campos sempre visíveis

## 9. Saída oficial

Fluxo oficial:

1. preencher
2. salvar
3. gerar `HTML`
4. opcionalmente exportar `PDF`

O registro oficial persistido é o dado estruturado no banco.

O `HTML` é o artefato principal gerado pela aplicação.

O `PDF` é apenas derivado do HTML quando solicitado pelo usuário.

## 10. Acessibilidade e UX

Requisitos:

- labels explícitos em todos os campos
- seções longas em blocos recolhíveis
- teclado funcional nas principais ações
- status e mensagens com texto claro
- comportamento consistente com tema claro/escuro

## 11. Critérios de aceite

- existe um novo item na sidebar chamado `Registros do SGM-FM`
- os 3 registros podem ser criados, editados, listados e excluídos
- `Rotina Diária` aceita múltiplos registros no mesmo dia para pontos diferentes
- a tela consegue sugerir dados operacionais já existentes
- o usuário consegue configurar campos visíveis por tipo de registro
- cada registro pode ser gerado em HTML
- o PDF é exportado sob demanda
- o módulo não interfere nos fluxos atuais de MPFM, SEP, Reconciliação, XML 042 e Exportação

## 12. Ordem recomendada de implementação

1. schema e backend CRUD
2. nova página e navegação
3. formulário da `Rotina Diária`
4. formulário do `Logbook`
5. formulário da `Análise PVT`
6. pré-preenchimento automático
7. visibilidade configurável de campos
8. geração HTML
9. exportação PDF
10. testes E2E
