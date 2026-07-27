# Matriz Operacional de Skills

## Objetivo

Este documento complementa o catalogo principal com uma visao direta de operacao:

- tipo de tarefa
- skills recomendadas
- ordem de uso
- exemplo de prompt

Use este arquivo quando a pergunta for pratica: "o que acionar agora?"

## Leitura Rapida

- `Principal`: skill que lidera a tarefa.
- `Complementar`: skill que apoia, valida ou fecha.
- `Ordem`: sequencia recomendada de uso.

## Matriz por Tipo de Tarefa

| Tipo de tarefa | Skill principal | Skills complementares | Ordem recomendada | Exemplo de prompt |
|---|---|---|---|---|
| Nova feature de front-end | `brainstorming` | `ux-designer`, `ui-ux-pro-max`, `ui-engineer`, `code-reviewer` | `brainstorming` -> `ux-designer` -> `ui-ux-pro-max` -> `ui-engineer` -> `code-reviewer` | "Use brainstorming e depois siga ate a implementacao da nova tela de resumo." |
| Novo componente UI | `brainstorming` | `ui-engineer`, `ui-ux-pro-max`, `code-reviewer` | `brainstorming` -> `ui-ux-pro-max` -> `ui-engineer` -> `code-reviewer` | "Crie um componente novo para cards de alerta usando ui-engineer." |
| Ajuste visual ou refinamento UX | `ui-ux-pro-max` | `ux-designer`, `ui-engineer`, `code-reviewer` | `ux-designer` -> `ui-ux-pro-max` -> `ui-engineer` -> `code-reviewer` | "Melhore a hierarquia visual dessa tela e depois implemente." |
| Nova feature de back-end | `brainstorming` | `architect`, `api-design`, `code-reviewer` | `brainstorming` -> `architect` -> `api-design` -> implementacao -> `code-reviewer` | "Planeje e implemente um novo modulo de API para reconciliacao." |
| Criacao ou revisao de API REST | `api-design` | `architect`, `code-reviewer` | `api-design` -> `architect` -> implementacao -> `code-reviewer` | "Desenhe a API REST desse recurso e revise os contratos." |
| Refactor estrutural | `architect` | `architecture`, `brainstorming`, `code-reviewer` | `brainstorming` -> `architecture` -> `architect` -> implementacao -> `code-reviewer` | "Proponha um refactor estrutural para separar melhor servicos e repositorios." |
| Bug funcional | `systematic-debugging` | `architecture`, `architect`, `code-reviewer` | `systematic-debugging` -> `architecture` -> correcao -> `code-reviewer` | "Use systematic-debugging para descobrir por que os dados saem errados." |
| Falha intermitente | `systematic-debugging` | `architecture`, `code-reviewer` | `systematic-debugging` -> instrumentacao -> correcao -> `code-reviewer` | "Investigue de forma sistematica por que esse teste falha as vezes." |
| Revisao de PR | `code-reviewer` | `architect`, `security-scan` | `code-reviewer` -> `architect` ou `security-scan` conforme risco | "Faca review desse PR com foco em regressao e arquitetura." |
| Testes e QA | `systematic-debugging` | `code-reviewer`, `architecture`, `gsd-planner` | `architecture` -> `systematic-debugging` -> ajustes -> `code-reviewer` | "Mapeie os impactos e monte um plano de QA para esta entrega." |
| Estabilizacao de release | `gsd-planner` | `systematic-debugging`, `code-reviewer`, `architecture` | `gsd-planner` -> `architecture` -> `systematic-debugging` -> `code-reviewer` | "Crie um plano por fases para estabilizar a release e reduzir risco." |
| Analise arquitetural | `architecture` | `architect`, `github-reader` | `architecture` -> `architect` -> plano ou recomendacao | "Explique a arquitetura do projeto e sugira pontos de melhoria." |
| Pesquisa de referencia externa | `github-reader` | `architect`, `api-design`, `ui-ux-pro-max` | `github-reader` -> skill especializada do contexto | "Leia esse repositorio e traga ideias para aplicar aqui." |
| Validacao de configuracao de agente | `security-scan` | `code-reviewer`, `architect` | `security-scan` -> ajustes -> `code-reviewer` | "Revise a configuracao do agente e procure riscos." |
| Texto tecnico ou documentacao | `readability` | `humanizer`, `detect` | `readability` -> `humanizer` -> `detect` se necessario | "Avalie a clareza desse documento e reescreva se precisar." |
| Follow-up ou comunicacao externa | `follow` | `humanizer`, `readability` | `follow` -> `humanizer` -> `readability` | "Escreva um follow-up curto, profissional e natural." |
| Conteudo com suspeita de IA | `detect` | `humanizer`, `readability` | `detect` -> `humanizer` -> `readability` | "Analise se esse texto parece de IA e reescreva se preciso." |
| Telegram input | `telegram-input` | `architect`, `systematic-debugging` | `architecture` -> `telegram-input` -> `systematic-debugging` | "Explique e ajuste o pipeline de entrada do bot Telegram." |
| Telegram output | `telegram-output` | `architect`, `systematic-debugging` | `architecture` -> `telegram-output` -> `systematic-debugging` | "Ajuste a saida do bot para audio e textos longos." |
| Tema de dominio de medicao | `oraculo-medicao` | `architect`, `architecture` | `oraculo-medicao` -> modelagem ou implementacao | "Explique essa regra de medicao e como refletir isso no sistema." |

## Atalhos Operacionais

### Se a tarefa for nova

- Comece por `brainstorming`.
- Se houver impacto estrutural, acione `architect`.
- Se houver API, acione `api-design`.
- Se houver interface, acione `ux-designer`, `ui-ux-pro-max` e `ui-engineer`.

### Se a tarefa estiver quebrada

- Comece por `systematic-debugging`.
- Use `architecture` se o problema atravessar varios modulos.
- Feche a correcao com `code-reviewer`.

### Se a tarefa for avaliar qualidade

- Comece por `code-reviewer`.
- Traga `architect` se houver risco estrutural.
- Traga `security-scan` se houver configuracao sensivel ou superficie de ataque.

### Se a tarefa for comunicar ou documentar

- Use `readability` para clareza.
- Use `humanizer` para tom.
- Use `follow` para mensagens de acompanhamento.

## Prompts Prontos

- "Use brainstorming para explorar a melhor abordagem antes de implementar."
- "Use systematic-debugging para encontrar a causa raiz desse bug."
- "Use architect para propor uma refatoracao segura."
- "Use api-design para modelar esse endpoint."
- "Use ui-ux-pro-max e ui-engineer para redesenhar e implementar essa tela."
- "Use code-reviewer para revisar minhas alteracoes."
- "Use gsd-planner para montar o plano por fases."
- "Use security-scan para revisar as configuracoes do agente."

## Relacao com o Catalogo Principal

Este arquivo e um atalho operacional.
O detalhamento por area, contexto, papel e exemplos adicionais esta em [CATALOGO_SKILLS_DESENVOLVIMENTO.md](C:/Users/mauri/OneDrive/Desktop/mpfm_app/docs/CATALOGO_SKILLS_DESENVOLVIMENTO.md).
