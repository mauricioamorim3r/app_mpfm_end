# MPFM App Design System

## Produto

Aplicação operacional para medição, reconciliação, separador, cards diários, QA e exportação técnica.

## Direção visual

- Base visual: `Real-Time Monitoring` + `Data-Dense Dashboard`
- Suavização: `Soft UI Evolution`
- Papel da interface: operação técnica, não marketing

## Princípios

- destacar dado operacional antes de metadata de arquivo
- tornar estados críticos legíveis em menos de 3 segundos
- reduzir ruído visual em telas densas
- separar resumo, ação, detalhe e auditoria
- preservar sensação de sistema sério, técnico e local

## Tokens de intenção

- `accent`: ação principal, foco, dado ativo
- `green`: dentro de faixa, valor validado, sucesso operacional
- `amber`: atenção, investigação, dado incompleto
- `red`: erro, falha, risco, fora de limite
- `purple`: dado comparativo ou reconciliado
- `muted`: metadata, contexto, suporte visual

## Superfícies

- Fundo base: o mais escuro e silencioso
- Painel primário: cards e blocos principais de leitura
- Painel secundário: filtros, subgrids, apoio
- Painel crítico: estados com borda/faixa reforçada

## Tipografia

- Títulos: claros, curtos, peso 700
- Subtítulos: explicam a leitura da seção
- Valores: `Space Mono`
- Tabelas e códigos: `IBM Plex Mono`

## Regras por componente

### Topbar
- deve acomodar filtros globais sem clipping
- em viewport pequeno deve quebrar linha

### KPI
- mostrar valor, contexto e período
- evitar excesso de texto no cabeçalho
- agrupar por leitura operacional, não por ordem técnica interna

### Tabelas
- cabeçalho sempre estável e legível
- densidade alta, mas sem perder contraste
- separar visualmente áreas comparativas e seções críticas

### Separador
- leitura em 4 blocos:
  - filtros
  - completude/arquivos
  - alinhamento/duplicidade
  - dados extraídos e fluidos

### Reconciliação
- leitura em 3 blocos:
  - cadastro PVT
  - execução
  - histórico
- sempre deixar claro o próximo passo

## Anti-padrões

- visual de landing page
- glassmorphism chamativo
- gradientes decorativos fortes
- excesso de bordas com mesmo peso
- texto explicativo perdido no meio da tabela
- ações críticas sem contraste ou contexto

## Responsividade

- desktop: prioridade para densidade controlada
- tablet: cards e blocos empilháveis
- mobile: topbar quebrada, KPIs em 2 colunas, sem corte horizontal

## Critério de aceite visual

- navegação principal claramente identificável
- ações críticas perceptíveis
- estados vazios úteis
- nenhuma região essencial cortada em 390px
- resumo, separador e recon legíveis sem esforço excessivo
