# Importação Soberana da `BASE_UNICA_MES`

Data: 2026-03-24  
Status: Draft aprovado para revisão do usuário

## Objetivo

Adicionar uma funcionalidade de recuperação operacional que permita importar um workbook mensal já conhecido pela aplicação e usar a aba `BASE_UNICA_MES` como fonte de verdade do mês.

Essa função existe para cenários excepcionais de recuperação, quando a ingestão normal por PDF/TXT falhou, ficou inconsistente ou não consegue mais refletir corretamente o estado desejado.

O resultado esperado é:

- a aplicação fica igual ao Excel importado para o mês afetado
- tudo que existir na aplicação e não existir no Excel deixa de existir no mês
- tudo que existir no Excel e não existir na aplicação passa a existir
- tudo que existir nos dois lados passa a refletir o valor do Excel

## Escopo

Entram nesta fase:

- importação de um arquivo `.xlsx`
- leitura da aba `BASE_UNICA_MES`
- validação estrutural da aba
- detecção do mês alvo
- preview do impacto
- substituição soberana do mês em `measurements_curated`
- recomposição dos dados derivados do mês
- atualização de outputs e estado mensal
- trilha operacional de execução

Ficam fora desta fase:

- importação de múltiplos meses em um único arquivo
- edição incremental célula a célula na UI
- importação de abas auxiliares que não sejam `BASE_UNICA_MES`
- mesclagem inteligente com dados manuais preexistentes

## Princípio Operacional

A aba `BASE_UNICA_MES` será tratada como fonte soberana para o mês importado.

Isso significa:

1. o workbook importado define o estado desejado do mês
2. a aplicação apaga o estado mensal atual relacionado à base operacional
3. a aplicação recarrega a base a partir da `BASE_UNICA_MES`
4. a aplicação recompõe tudo o que depende dessa base

Não haverá reconciliação por merge entre Excel e banco.

## Abordagem Escolhida

Foi escolhida a abordagem de **substituição completa do mês**.

Motivos:

- é a forma mais segura de garantir coerência final
- evita resíduos de dados antigos
- evita regras complexas de merge e conflito
- atende o requisito de “ficar como se sempre tivesse sido daquele jeito”

## Fonte de Dados

A importação lerá exclusivamente:

- aba: `BASE_UNICA_MES`

As colunas da aba devem seguir o layout produzido pela exportação mensal da aplicação.

Os campos mínimos esperados incluem:

- `ProductionDate`
- `Hour`
- `Granularity`
- `Origin`
- `SourceType`
- `Bank`
- `Loop`
- `Tipo`
- `Tag`
- `Instrumento`
- `Fonte`
- `SourceFile`
- `IsOfficial`

Além das colunas métricas já existentes no layout da `BASE_UNICA_MES`.

## Mapeamento de Persistência

### Tabela-base

O destino primário da importação será:

- `measurements_curated`

Cada linha da `BASE_UNICA_MES` será convertida em múltiplas linhas normalizadas de métrica, respeitando:

- `day_ref`
- `hour_ref`
- `row_kind`
- `bank`
- `loop`
- `tipo`
- `tag`
- `instrument`
- `metric_name`
- `metric_value`
- `source_file`
- `is_official`

### Regras de normalização

- `Granularity = Hourly` e origem MPFM: `row_kind = hourly`
- `Granularity = Daily` e origem MPFM: `row_kind = daily`
- `Origin = RECON`: `row_kind = recon`
- `Origin = SEP`: `row_kind = sep`
- `Hour` vazio: `hour_ref = null`
- `Hour = HH:00`: `hour_ref = HH`

### Campos derivados do layout

Os nomes de coluna da `BASE_UNICA_MES` serão convertidos para os `metric_name` já usados no banco, preservando a taxonomia atual da aplicação.

## Comportamento de Substituição

Ao aplicar a importação de um mês:

1. identificar o mês alvo a partir de `ProductionDate`
2. validar que a planilha contém um único mês
3. criar backup local antes de escrever
4. apagar o recorte mensal atual das áreas operacionais
5. reimportar o conteúdo da `BASE_UNICA_MES`
6. recompor o que depende da base importada

## Itens que serão limpos e recompostos

### Limpeza direta do mês

- `measurements_curated`
- `validation_issues`
- `daily_cards`
- `daily_card_edits`
- `mpfm_monitoring_daily`
- `tpoc_daily_potential_curated`
- `xml042_documents`
- `sep_alignments` do mês, se estiverem derivados de estado operacional
- entradas do `state_YYYY_MM.json`

### Itens a regenerar após a carga

- `validation_issues` do mês
- `state_YYYY_MM.json`
- workbook mensal
- cards diários
- leituras de resumo por banco/TAG
- estruturas consumidas por `Resumo do Mês`
- candidatos/estado de `XML 042`
- visão de `Monitoramento MPFM`

## Itens que não serão preservados por merge

Os módulos abaixo não serão mesclados com o estado anterior. Eles serão recompostos ou esvaziados para ficarem coerentes com a nova base:

- `Cards Diários`
- `Monitoramento MPFM`
- `XML 042`

Motivo:

Esses módulos podem conter decisões ou estados manuais incompatíveis com a nova `BASE_UNICA_MES`.

## UI

Será adicionada uma nova ação de recuperação/importação operacional.

Local recomendado:

- `Processar Arquivos`
ou
- `Config. > Recuperação operacional`

Fluxo:

1. selecionar o arquivo `.xlsx`
2. validar a existência da aba `BASE_UNICA_MES`
3. validar colunas obrigatórias
4. detectar mês alvo
5. mostrar preview:
   - total de linhas válidas
   - dias afetados
   - bancos afetados
   - linhas novas
   - linhas substituídas
   - linhas que deixarão de existir
6. exigir confirmação explícita
7. aplicar a importação
8. mostrar log final

## Segurança Operacional

Esta funcionalidade é destrutiva no recorte mensal.

Proteções obrigatórias:

- validação estrutural antes de qualquer escrita
- recusa se houver mais de um mês na aba
- recusa se faltarem colunas obrigatórias
- recusa se o arquivo não for um workbook válido
- backup local antes da operação
- transação no banco
- só atualizar `state` e outputs após sucesso de persistência

## Acessibilidade

Como é uma ação de recuperação crítica, a UI precisa:

- rótulos claros para upload, preview e confirmação
- mensagens de erro textuais
- foco previsível após validação e conclusão
- log legível via região anunciável (`aria-live`) quando aplicável

## Logs e Auditoria

A operação deve gerar um registro operacional com:

- nome do arquivo importado
- mês alvo
- quantidade de linhas lidas
- quantidade de métricas persistidas
- quantidade de dias afetados
- horário da execução
- status final
- mensagem de erro, se houver

## Riscos Conhecidos

1. workbook exportado manualmente e editado com colunas quebradas
2. mistura de mais de um mês dentro da `BASE_UNICA_MES`
3. perda de estados manuais que não sejam compatíveis com a base soberana
4. importação de valores incoerentes por erro humano no Excel

## Mitigações

- validação rígida da estrutura
- preview antes de aplicar
- confirmação dupla
- backup local
- recomposição total do mês

## Critérios de Aceite

1. importar um workbook mensal válido substitui o mês inteiro na aplicação
2. telas do mês passam a refletir exclusivamente o conteúdo importado
3. dados antigos do mês ausentes no Excel deixam de existir na aplicação
4. dados presentes no Excel e ausentes no banco passam a existir
5. após importação, `Resumo`, `MPFM`, `Separador`, `Cards`, `Monitoramento` e `Exportar` ficam coerentes com a nova base
6. a operação falha sem efeitos parciais quando a planilha for inválida

## Estratégia de Implementação

1. criar serviço isolado de importação da `BASE_UNICA_MES`
2. criar parser/validador estrutural da aba
3. criar preview do impacto
4. criar rotina de purge mensal controlado
5. persistir nova base do mês
6. recompor derivados
7. adicionar UI com confirmação explícita
8. validar com base real e planilha editada
