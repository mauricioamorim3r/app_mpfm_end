# Catalogo de Skills para Desenvolvimento de Aplicacoes

## Objetivo

Este documento organiza as skills que podemos acionar durante o desenvolvimento de uma aplicacao, cobrindo front-end, back-end, arquitetura, debugging, revisao, testes, QA e comunicacao tecnica.

O foco aqui e operacional: saber rapidamente qual skill usar, em que momento usar e quais combinacoes funcionam melhor no trabalho do dia a dia.

## Como Ler Este Catalogo

- `Skill principal`: skill que normalmente lidera aquele tipo de trabalho.
- `Skill complementar`: skill que entra para refinar, validar ou fechar a entrega.
- `Quando usar`: gatilho pratico de uso.
- `Quem usa`: perfil que mais se beneficia daquela skill.

## Regras Praticas de Uso

- Em trabalho criativo, desenho de feature ou mudanca de comportamento, comecar por `brainstorming`.
- Em bugs, falhas de teste ou comportamento inesperado, comecar por `systematic-debugging`.
- Apos alteracoes relevantes de codigo, passar por `code-reviewer`.
- Quando a tarefa tocar arquitetura, nao improvisar: usar `architect` ou `architecture`.
- Em UI, separar bem estrategia de experiencia (`ux-designer`, `ui-ux-pro-max`) da implementacao (`ui-engineer`).

## 1. Planejamento, Descoberta e Arquitetura

| Skill | Papel | Quando usar | Quem usa | Exemplo de pedido |
|---|---|---|---|---|
| `brainstorming` | Principal | Antes de criar feature, fluxo, componente ou comportamento novo | Dev, Product, UX | "Use brainstorming para definir a melhor forma de implementar esta funcionalidade." |
| `architect` | Principal | Quando houver decisao estrutural, refactor grande, separacao de modulos ou escalabilidade | Tech lead, Dev senior | "Use architect para propor a arquitetura desta evolucao." |
| `architecture` | Complementar | Para explicar a visao macro do sistema atual e impactos de mudanca | Dev, QA, gestor tecnico | "Explique a arquitetura atual e onde essa feature entra." |
| `gsd-planner` | Complementar | Para quebrar um objetivo em fases executaveis e dependencias | Dev, PM, Tech lead | "Monte um plano em fases para entregar esta feature." |
| `github-reader` | Complementar | Quando precisarmos estudar um repositorio e extrair ideias, padroes ou referencias | Dev, revisor tecnico | "Leia esse repositorio e sugira a melhor abordagem." |

## 2. Front-end, UI e UX

| Skill | Papel | Quando usar | Quem usa | Exemplo de pedido |
|---|---|---|---|---|
| `ui-engineer` | Principal | Para implementar telas, componentes, estilos, responsividade e acessibilidade basica | Front-end, full stack | "Implemente esta tela com ui-engineer mantendo boa estrutura CSS." |
| `ui-ux-pro-max` | Principal | Para fortalecer identidade visual, layout, hierarquia, tipografia e refinamento visual | UI designer, front-end | "Redesenhe esta pagina com ui-ux-pro-max." |
| `ux-designer` | Principal | Para desenhar fluxo do usuario, usabilidade, formularios e jornadas | UX, product, front-end | "Use ux-designer para melhorar o fluxo desse cadastro." |
| `brainstorming` | Complementar | Para validar alternativas antes de construir a interface | Front-end, UX | "Antes de codar, explore opcoes para essa nova tela." |
| `code-reviewer` | Complementar | Para revisar risco funcional, regressao visual e manutencao do componente | Front-end, revisor | "Revise essa implementacao de UI com foco em regressao." |

## 3. Back-end, API e Regras de Negocio

| Skill | Papel | Quando usar | Quem usa | Exemplo de pedido |
|---|---|---|---|---|
| `api-design` | Principal | Ao desenhar endpoints, contratos, recursos, filtros, codigos HTTP e padroes REST | Back-end, full stack | "Desenhe a API REST para este modulo." |
| `architect` | Principal | Ao separar camadas, servicos, repositorios, eventos ou fronteiras entre modulos | Back-end, lead tecnico | "Proponha a arquitetura dessa refatoracao do backend." |
| `systematic-debugging` | Principal | Quando uma regra falha, o dado fica inconsistente ou a API responde errado | Back-end, QA, suporte tecnico | "Investigue sistematicamente por que este endpoint retorna dados errados." |
| `architecture` | Complementar | Para mapear fluxo atual de dados antes da mudanca | Back-end, QA | "Explique como esse dado entra, e processado e persistido." |
| `code-reviewer` | Complementar | Para revisar seguranca basica, riscos de regressao e manutencao do codigo | Back-end, revisor tecnico | "Faca code review desta mudanca de backend." |

## 4. Debugging, Incidentes e Analise de Problemas

| Skill | Papel | Quando usar | Quem usa | Exemplo de pedido |
|---|---|---|---|---|
| `systematic-debugging` | Principal | Sempre que houver bug, falha intermitente, erro em producao ou comportamento inesperado | Dev, QA, suporte | "Use systematic-debugging para achar a causa raiz desse bug." |
| `architecture` | Complementar | Quando o problema exigir entender fluxos macro e dependencias entre modulos | Dev, QA | "Mapeie a arquitetura envolvida nesse bug." |
| `memory` | Complementar | Para duvidas sobre memoria, persistencia de contexto ou historico do agente | Dev, operador do agente | "Explique como a memoria esta influenciando este comportamento." |
| `security-scan` | Complementar | Quando o erro ou risco estiver ligado a configuracao de agentes, prompts ou integracoes | Dev, AppSec, revisor | "Faca um scan nas configuracoes do agente." |
| `code-reviewer` | Complementar | Para validar se a correcao realmente fecha o problema sem abrir regressao | Dev, revisor tecnico | "Revise a correcao proposta para esse bug." |

## 5. Revisao Tecnica e Qualidade de Codigo

| Skill | Papel | Quando usar | Quem usa | Exemplo de pedido |
|---|---|---|---|---|
| `code-reviewer` | Principal | Depois de alterar codigo, ao revisar PR ou validar risco de regressao | Dev, reviewer, lead | "Revise este PR com foco em bugs e regressao." |
| `architect` | Complementar | Quando a revisao precisa avaliar direcao estrutural, acoplamento e limites de modulo | Lead tecnico, arquiteto | "Avalie se esta mudanca piora a arquitetura." |
| `readability` | Complementar | Quando for importante medir clareza de texto, docs, descricoes ou comunicacoes | Dev, QA, documentacao | "Avalie a legibilidade deste texto tecnico." |
| `detect` | Complementar | Quando houver necessidade de avaliar se um texto parece gerado por IA | Editor, marketing, autor | "Analise se esse texto parece de IA." |
| `humanizer` | Complementar | Quando quisermos reescrever um texto para soar mais natural e humano | Autor, gestor, comercial | "Humanize esta explicacao tecnica." |

## 6. Testes, QA e Validacao

| Skill | Papel | Quando usar | Quem usa | Exemplo de pedido |
|---|---|---|---|---|
| `systematic-debugging` | Principal | Para investigar falhas de teste, inconsistencias de ambiente e bugs reproduziveis | QA, Dev, suporte | "Investigue por que este teste falha de forma intermitente." |
| `code-reviewer` | Principal | Para revisar cobertura, riscos nao testados e regressao funcional | QA, reviewer, Dev | "Revise essas mudancas olhando principalmente os testes." |
| `brainstorming` | Complementar | Para desenhar estrategia de validacao antes de executar mudancas grandes | QA, Dev, lead | "Defina uma estrategia de QA para essa entrega." |
| `gsd-planner` | Complementar | Para montar fases de estabilizacao, rollout, reteste e aceite | QA lead, PM, Dev | "Crie um plano por fases para estabilizar essa release." |
| `architecture` | Complementar | Para entender os pontos do sistema que devem ser validados | QA, Dev | "Mapeie os modulos impactados para eu testar direito." |

## 7. Seguranca e Configuracao de Agentes

| Skill | Papel | Quando usar | Quem usa | Exemplo de pedido |
|---|---|---|---|---|
| `security-scan` | Principal | Ao revisar configuracoes de agentes, prompts, integracoes e riscos de injecao | AppSec, Dev, revisor | "Faca um scan de seguranca nessas configuracoes." |
| `code-reviewer` | Complementar | Para procurar fragilidades no codigo mudado junto com a configuracao | Dev, reviewer | "Revise a mudanca com foco em riscos e manutencao." |
| `architect` | Complementar | Quando a seguranca depender de limites claros entre modulos e responsabilidades | Arquiteto, lead tecnico | "Reveja a arquitetura sob a lente de seguranca operacional." |

## 8. Conteudo, Comunicacao e Documentacao

| Skill | Papel | Quando usar | Quem usa | Exemplo de pedido |
|---|---|---|---|---|
| `follow` | Principal | Para follow-ups, cobrancas elegantes, retomada de conversa e reengajamento | Comercial, gestor, suporte | "Escreva um follow-up curto e eficaz para esse cliente." |
| `humanizer` | Principal | Para deixar um texto mais natural, menos mecanico e mais convincente | Autor, gestor, marketing | "Reescreva esse texto para soar mais humano." |
| `readability` | Principal | Para medir clareza e dificuldade de leitura em texto tecnico ou operacional | Autor, QA, documentacao | "Avalie a legibilidade desse manual." |
| `detect` | Complementar | Quando houver necessidade de verificar tracos de IA em textos publicados | Editor, revisor | "Me diga se este texto parece gerado por IA." |
| `github-reader` | Complementar | Para estudar documentacao ou estrutura de repositorios externos como referencia | Dev, autor tecnico | "Leia esse repositorio e resuma as ideias principais." |

## 9. Skills de Dominio ou Contexto Especifico

| Skill | Papel | Quando usar | Quem usa | Exemplo de pedido |
|---|---|---|---|---|
| `oraculo-medicao` | Principal | Em assuntos de medicao de petroleo, gas, hidrocarbonetos e metrologia | Especialista de dominio, Dev, analista | "Explique essa regra de medicao de hidrocarbonetos." |
| `telegram-input` | Principal | Em arquitetura de entrada do bot Telegram, audio, PDF, Markdown e extracao local | Dev de integracao, bot engineer | "Explique a arquitetura de entrada do bot Telegram." |
| `telegram-output` | Principal | Em arquitetura de saida do bot Telegram, audio, chunking e geracao de arquivos | Dev de integracao, bot engineer | "Ajuste a saida do bot para textos grandes e audio." |
| `memory` | Complementar | Quando o trabalho envolver contexto persistente do agente ou historico operacional | Dev, operador do agente | "Explique o papel da memoria neste fluxo." |

## Combinacoes Recomendadas por Tipo de Trabalho

### Nova feature de front-end

- `brainstorming` para entender a necessidade e fechar a direcao.
- `ux-designer` para fluxo e usabilidade.
- `ui-ux-pro-max` para linguagem visual.
- `ui-engineer` para implementacao.
- `code-reviewer` para revisar risco e regressao.

### Nova feature de back-end

- `brainstorming` para alinhar escopo e contratos.
- `architect` para estrutura e fronteiras.
- `api-design` para modelar a interface da API.
- `systematic-debugging` se houver comportamento inesperado na integracao.
- `code-reviewer` para fechamento tecnico.

### Correcao de bug

- `systematic-debugging` para descobrir causa raiz.
- `architecture` se o bug atravessar varios modulos.
- `architect` se a causa for estrutural.
- `code-reviewer` para revisar a correcao.

### Revisao de PR ou mudanca delicada

- `code-reviewer` como skill principal.
- `architect` se a mudanca alterar limites de modulo.
- `security-scan` se houver config de agente, prompt ou integracao sensivel.

### QA e estabilizacao

- `systematic-debugging` para falhas e reproducoes.
- `architecture` para mapear impacto.
- `gsd-planner` para organizar ciclos de estabilizacao.
- `code-reviewer` para garantir que a mudanca nao abriu novas regressoes.

### Documentacao ou comunicacao com stakeholder

- `readability` para medir clareza.
- `humanizer` para melhorar o tom.
- `follow` para mensagens de acompanhamento.
- `detect` se houver necessidade de inspecionar sinais de texto gerado por IA.

## O Que Essas Skills Nao Substituem

- Nao substituem entendimento do codigo real do repositorio.
- Nao substituem testes, validacao funcional e verificacao em ambiente.
- Nao substituem decisoes de negocio ou de dominio quando faltarem requisitos.
- Nao substituem revisao humana em mudancas sensiveis.

## Regra de Operacao Recomendada

Para a maioria dos trabalhos de aplicacao, este fluxo tende a funcionar bem:

1. Entender e desenhar com `brainstorming`.
2. Estruturar com `architect` ou `api-design` quando necessario.
3. Implementar com a skill especializada do contexto.
4. Investigar com `systematic-debugging` sempre que algo sair do esperado.
5. Fechar com `code-reviewer`.

## Resumo Executivo

Se a tarefa for nova, comece por `brainstorming`.
Se estiver quebrado, comece por `systematic-debugging`.
Se mexer em estrutura, use `architect`.
Se mexer em API, use `api-design`.
Se mexer em interface, use `ux-designer`, `ui-ux-pro-max` e `ui-engineer`.
Se terminou uma mudanca relevante, passe por `code-reviewer`.
