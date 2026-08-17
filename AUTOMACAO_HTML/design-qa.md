# QA visual do dashboard — 13/08/2026

## Evidências

- Referência principal: `ChatGPT Image 12 de ago. de 2026, 23_34_48.png` (1680 × 945).
- Referência da cadeia: `ChatGPT Image 12 de ago. de 2026, 23_36_27.png` (1536 × 1024).
- Implementação: `BASE_UNICA_TOTAL_RELATORIO_COMPLETO.html`.
- Viewport conferido: 1363 × 936, escala 100%, estado inicial com todos os pontos e todos os pares.

## Comparação visual

- Estrutura: cabeçalho compacto, navegação lateral fixa, barra de filtros aberta, KPIs e conteúdo analítico em cartões, seguindo a hierarquia da referência sem copiar campos inexistentes.
- Conteúdo: somente variáveis disponíveis na Base Única/PI/Comparativo; ausências aparecem como `Sem dado`.
- Segunda tela: cadeia em seis estágios, inspirada no fluxo sequencial da referência, sem adicionar sensores ou controles não disponíveis.
- Separador: fonte independente, sem alinhamento automático; comparação permanece uma escolha do usuário.

## Interações verificadas

- Filtro de ponto: 38 registros/8 medidores → 6 registros/1 medidor para PE-02.
- Navegação para `Cadeia do dado`: seis estágios renderizados.
- Três pares físicos presentes na visão integrada.
- Caso de referência próxima de zero: percentual suprimido e status explícito.
- Sem overflow horizontal no viewport desktop.

## Iterações de correção

- P1: painéis inicialmente vazios por erros sintáticos no JavaScript; corrigido e revalidado.
- P1: desvio extremo sobre referência quase zero e interpretação indevida dos códigos de status PI como alertas; ambos corrigidos.
- Validação final: 20 testes automatizados, dois manifests Excel→HTML aprovados e 9 scripts executáveis por HTML sem erro sintático.

## Resultado

passed
