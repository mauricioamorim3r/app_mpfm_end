# Plano de Refatoração do Frontend e da Comparação por FC

## Objetivo

Redesenhar a experiência principal da aplicação para o uso diário com arquivos Flow-X, reduzindo explicações na tela e organizando o fluxo em torno de:

1. carregar o arquivo do dia
2. identificar os FCs encontrados
3. escolher com qual arquivo cada FC será comparado
4. mostrar o que mudou com destaque para o que importa
5. separar ações humanas, automáticas e de processo
6. permitir o uso de referências fixas e referências vivas

## Base operacional observada

Os arquivos reais mostraram um padrão típico de operação:

- 4 FCs por dia: `21JN101A`, `21JN101B`, `21JN102A`, `21JN102B`
- 1 `Configuration` + 1 `Events_Snapshot` por FC
- exceções precisam ser suportadas, como `21JN107` em `02/04/2026`
- a data interna do relatório é mais confiável que o nome do ZIP

## Escopo desta refatoração

### Backend

- adicionar endpoint para candidatos de comparação por `batch + FC`
- detectar automaticamente a melhor opção de `dia anterior`
- listar versões históricas disponíveis por FC
- enriquecer o diff com:
  - metadados dos dois lados
  - valor de referência, quando existir
  - status de referência: `ok`, `desvio`, `critical`
- criar referências dinâmicas para:
  - `densidade`
  - `cromatografia / GC`

### Frontend

- remover os blocos longos de explicação espalhados na tela
- reorganizar a aplicação em áreas operacionais:
  - `Entrada`
  - `Comparação`
  - `Resultado`
  - `Intervenções`
  - `Configurações`
- dar destaque visual ao arquivo carregado e ao arquivo usado na comparação
- permitir comparação automática com o dia anterior
- avisar claramente quando o dia anterior não existir
- permitir escolha manual por:
  - `FC`
  - `data`
  - `nome do arquivo`

## Regras de comparação

### Referência fixa

Continuam configuráveis manualmente:

- `pulse mode`
- `IP / máscara / gateway`
- `Modbus / HART`
- `range / escala`
- `parâmetros críticos marcados manualmente`

### Referência viva

Usar referência dinâmica confirmada pelo usuário para:

- `densidade`
- `cromatografia / GC`

Fluxo:

1. a aplicação lê o valor no arquivo carregado
2. verifica se já existe referência salva para aquele FC
3. se não existir, oferece salvar o valor atual como referência
4. se já existir, compara com a referência atual e permite salvar a nova leitura como nova referência

## Resultado esperado

O resultado da comparação deve responder rapidamente:

- qual FC está sendo analisado
- qual arquivo foi carregado
- qual arquivo foi usado para comparar
- o que mudou
- o que é crítico
- o que foi ação humana
- o que foi ação automática
- o que foi processo
- o que está fora da referência

## Destaques obrigatórios

O topo do resultado deve priorizar:

- `standard density override`
- `pulse mode / single vs dual pulse`
- `overrides habilitados`
- `falha de login`
- `login/logout`
- `print configuration report`
- `print snapshot report`
- `alarmes de vazão baixa-baixa`

Depois:

- `IP / Modbus / HART / ranges / canais`

## Linha do tempo de intervenção

Criar uma visão dedicada para a janela operacional:

- `Humano`
  - login
  - logout
  - failed login
  - print report
  - print snapshot
- `Automático / integração`
  - alterações por `CommDrivers`
- `Processo`
  - alarmes e eventos de run

## Fases de entrega

### Fase 1

- backend de comparação por FC
- backend de referência viva
- diff enriquecido
- tipos do frontend atualizados

### Fase 2

- nova tela `Entrada`
- nova tela `Comparação`
- nova tela `Resultado`

### Fase 3

- nova tela `Intervenções`
- ajustes em `Configurações`
- refinamento visual

### Fase 4

- validação completa:
  - `compileall`
  - `build`
  - `lint`
  - teste visual na tela

## Critérios de pronto

- o usuário consegue carregar um ZIP e ver os FCs encontrados
- para cada FC, a aplicação oferece o dia anterior quando existir
- quando não existir dia anterior, o aviso fica claro
- o usuário consegue escolher outro arquivo por data/nome/FC
- a comparação mostra os dois lados com metadados
- a comparação destaca mudanças críticas
- densidade e cromatografia podem ser salvas como referência viva
- a aplicação compara leituras novas com a referência viva salva
- a tela de intervenções separa humano, automático e processo
