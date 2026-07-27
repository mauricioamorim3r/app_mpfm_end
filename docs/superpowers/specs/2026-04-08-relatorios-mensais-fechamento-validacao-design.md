# Relatórios Mensais de Fechamento e Validação - Design

Data: 2026-04-08
Status: Draft aprovado para revisão do usuário

## 1. Objetivo

Adicionar um novo módulo de `Relatórios Mensais` à aplicação para permitir geração de relatórios executivos de fechamento e validação dos dados medidos e reportados ao longo do mês.

O relatório deve consolidar:

- medições MPFM por dia
- valores do separador de testes
- arquivos XML 042 gerados e/ou importados
- exceções e problemas de qualidade dos dados
- visão executiva do mês
- tabelas específicas por grupo `MPFM × Riser`

O artefato principal deve ser exibido em `HTML` dentro da aplicação e exportável para `PDF`.

## 2. Escopo da primeira entrega

Entram nesta fase:

- novo item na sidebar: `Relatórios Mensais`
- tela própria com geração sob demanda do relatório mensal
- relatório executivo consolidado do mês
- seção específica para arquivos ANP/XML enviados
- seções tabulares por grupo `MPFM × Riser`
- seção de exceções e validação
- modo padrão com grupos pré-definidos
- modo customizado com escolha manual de grupo/recorte
- saída em `HTML`
- exportação para `PDF`

Ficam para fase posterior:

- agendamento automático mensal
- assinatura/aprovação formal do relatório
- versionamento histórico do relatório gerado
- envio automático por e-mail
- exportação adicional estruturada em Excel nesta mesma tela

## 3. Princípio operacional

O relatório mensal deve ser uma visão de fechamento, não uma nova base de cálculo independente.

Ele deve consumir como fonte oficial as estruturas já consolidadas na aplicação, de forma coerente com:

- tabelas mensais do sistema
- XMLs gerados/enviados
- dados do separador
- reconciliação
- alertas e validações

O relatório deve mostrar dias com campos vazios quando não houver dado.

Regra importante:

- campo vazio = não houve dado
- valor `0` = houve dado e o valor foi zero

## 4. Saída e formato

### 4.1 Saída principal

- visualização em `HTML` dentro da aplicação
- exportação sob demanda em `PDF`

### 4.2 Filosofia da leitura

O relatório deve equilibrar:

- visão gerencial/executiva
- rastreabilidade técnica
- leitura simples para fechamento mensal

## 5. Estrutura do relatório

## 5.1 Resumo Executivo

Deve abrir o relatório e trazer:

- mês de referência
- grupos considerados
- total de dias com dado no mês
- totais mensais medidos
- totais mensais reportados no XML 042
- quantidade de XMLs gerados/enviados/importados
- cobertura de dados do mês
- destaque das principais exceções

## 5.2 XMLs ANP / Arquivos 042

Seção com todos os XMLs do mês, considerando gerados e/ou importados.

Colunas mínimas:

- data de produção
- código do poço
- poço
- TAG subsea
- banco
- óleo
- gás
- água
- arquivo
- status do XML

Objetivo:

- permitir conferência do que foi efetivamente enviado/reportado à ANP

## 5.3 Tabelas por grupo MPFM × Riser

Cada grupo deve ter uma tabela própria.

Grupos padrão iniciais:

- `PE_4 × Riser P5`
- `PE_2 × Riser P2`
- `PW-104DA × Riser P4`

Cada linha representa um dia do mês.

Colunas mínimas:

- `Data`
- `Óleo massa MPFM`
- `Gás massa MPFM`
- `Água massa MPFM`
- `%HC`
- `%Total`
- `Óleo volume`
- `Gás volume`
- `Água volume`
- `Óleo separador`
- `Gás separador`
- `Água separador`
- `Óleo XML`
- `Gás XML`
- `Água XML`

### 5.3.1 Regra de `%HC` e `%Total`

Nesta entrega:

- `%HC` = participação de hidrocarbonetos no balanço do dia
- `%Total` = participação do total no balanço do dia

Esses percentuais não representam desvio entre fontes.

## 5.4 Exceções e Validação

Seção dedicada a qualidade do dado e pendências do mês.

Subseções mínimas:

- dias sem XML
- dias com hourly incompleto
- dias com reconciliação parcial
- dias com status `VERIFICAR`
- dias sem dado de separador ou sem alinhamento válido

O objetivo é permitir que o fechamento mensal mostre não apenas os números, mas também a confiança operacional do mês.

## 6. Modo padrão e modo customizado

## 6.1 Modo padrão

O usuário gera o relatório com:

- mês selecionado
- grupos padrão já definidos na aplicação

Esse é o fluxo principal do fechamento mensal.

## 6.2 Modo customizado

Se o usuário desejar análise específica, deve existir opção para:

- escolher grupo específico
- escolher banco
- escolher intervalo de datas
- gerar relatório apenas com aquele recorte

O modo customizado não substitui o padrão; ele complementa a análise.

## 7. Fontes de dados

O relatório deve usar como base:

- `measurements_curated`
- `recon_runs`
- `validation_issues`
- `xml042_documents`
- `xml042_imported_rows`
- `sep_alignments`
- `sep_source_files`
- detalhes do separador em `measurements_curated`
- pares padrão usados no monitoramento e gráficos

## 8. Regras de negócio

### 8.1 Visibilidade dos dias

Todos os dias do recorte devem aparecer nas tabelas do grupo.

Mesmo que não exista dado em uma ou mais fontes, o dia deve continuar visível.

### 8.2 Dados ausentes

Se não houver dado em determinada fonte:

- mostrar campo vazio

### 8.3 Valor zero

Se houver dado igual a zero:

- mostrar `0`

### 8.4 XML do mês

Quando houver dados tanto em `xml042_documents` quanto em `xml042_imported_rows`, o relatório deve priorizar a fonte mais adequada para representar o que foi enviado/reportado no mês.

Regra recomendada para a primeira fase:

- usar `xml042_documents` como referência oficial de XML gerado pelo sistema
- usar `xml042_imported_rows` como complemento para conferência/importação retroativa

## 9. Arquitetura recomendada

## 9.1 Backend

Novos componentes sugeridos:

- `routes/monthly_reports_routes.py`
- `services/monthly_reports/monthly_reports_service.py`
- `services/monthly_reports/monthly_reports_render_service.py`

Responsabilidades:

- rota: filtros, geração e exportação
- serviço: coleta, agregação e cálculo das seções
- render: HTML do relatório e exportação PDF

## 9.2 Frontend

Novos componentes sugeridos:

- nova página em `index.html`
- `static/app.monthly_reports.js`
- estilos complementares em `static/app.layout.css`

## 10. UX e acessibilidade

Requisitos:

- novo item na sidebar: `Relatórios Mensais`
- seletor de mês
- seletor de modo `Padrão` / `Customizado`
- filtros claros no modo customizado
- botão `Gerar relatório`
- botão `Exportar PDF`
- indicadores com `aria-live` para status de geração
- leitura consistente nos temas claro e escuro
- tabelas com cabeçalhos explícitos e ordem previsível

## 11. Sugestão adicional incorporada

O relatório deve incluir uma mini seção de `Conciliação Medido × Reportado`, resumindo o mês por:

- MPFM
- Separador
- XML ANP

Objetivo:

- apoiar o fechamento mensal
- facilitar leitura executiva das diferenças entre medido e reportado

## 12. Critérios de aceite

- existe um novo módulo `Relatórios Mensais` na sidebar
- o usuário consegue gerar relatório mensal em HTML
- o relatório traz resumo executivo do mês
- o relatório traz tabela de XMLs ANP do mês
- o relatório traz seções por grupo `MPFM × Riser`
- o relatório mostra dias sem dado com campo vazio
- o relatório preserva `0` quando o valor real for zero
- existe seção de exceções e validação
- o usuário pode gerar relatório customizado para grupo/recorte específico
- o relatório pode ser exportado em PDF

## 13. Ordem recomendada de implementação

1. backend de agregação mensal
2. modelo de grupos padrão
3. render HTML do relatório
4. nova página e navegação
5. modo padrão
6. modo customizado
7. seção de XMLs enviados/importados
8. seção de exceções
9. exportação PDF
10. testes E2E
