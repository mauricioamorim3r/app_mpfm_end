# Desenho de Comparação por Dois Arquivos e TAG

## Objetivo

Adicionar um fluxo mais rápido de comparação que aceite:

- `arquivo atual`
- `arquivo para comparar`

A aplicação deve ler os dois ZIPs, identificar os `FCs` e, dentro de cada FC, identificar as `TAGs` e comparar as configurações da mesma TAG entre os dois dias.

## Regras principais

1. O segundo arquivo é opcional.
2. Quando os dois arquivos forem carregados, a aplicação deve:
   - sugerir pares por `FC`
   - dentro de cada FC, sugerir pares por `TAG`
   - esperar a confirmação do usuário antes de gerar a comparação
3. Quando só um arquivo for carregado, o fluxo atual continua válido:
   - usar histórico
   - usar importação anterior
   - permitir escolha manual

## Modelo mental

- `FC` = contêiner principal da configuração
- `TAG` = elemento configurável dentro do FC
- `comparação` = mesma TAG em dias diferentes
- `referência` = valor esperado ou referência viva usada para validar a leitura

## Entrada

A área de entrada passa a ter dois blocos:

- `Arquivo atual`
- `Arquivo para comparar`

Cada bloco mostra:

- nome do ZIP
- data interna encontrada
- FCs encontrados
- status da leitura

## Pareamento

Após a leitura, a aplicação deve montar sugestões por FC:

- `FC encontrado no arquivo atual`
- `FC correspondente no arquivo de comparação`
- quantidade de TAGs identificadas
- quantidade de TAGs com par sugerido
- quantidade de TAGs sem par

O usuário confirma a comparação por FC antes de abrir o resultado.

## Resultado

O resultado deve mostrar:

### Cabeçalho

- arquivo atual
- arquivo comparado
- FC
- data/hora
- serial
- IP
- application version
- application date/time

### Resumo por FC

- tags identificadas
- tags com mudança
- tags sem correspondência
- tags que bateram com referência

### Detalhe por TAG

Para cada TAG:

- valor antigo
- valor novo
- valor de referência, quando existir
- status: `ok`, `desvio`, `crítico`

## Identificação de TAGs

Os arquivos Flow-X devem ser tratados com contexto estrutural. O parser precisa guardar blocos como:

- `Run 1`, `Run 2`
- `Product 1`
- `Analog input 1`
- `Pt100 input 1`
- `Digital input`

Quando houver uma linha com `Tag` ou `Meter tag`, essa TAG passa a identificar o bloco. Os parâmetros seguintes daquele bloco devem ser persistidos com contexto suficiente para comparação entre dias.

## Referências

### Referência viva

Para:

- densidade
- cromatografia / GC

Comportamento:

- se não existir referência, perguntar se o valor atual deve virar referência
- se já existir referência, permitir comparar ou substituir

### Referência fixa

Para:

- pulse mode
- IP / máscara / gateway
- Modbus / HART
- range / escala
- parâmetros críticos

## Base de mapeamento editável

Em `Configurações`, criar uma base com CRUD para o mapeamento operacional:

- `ID CV`
- `CV Tag Device`
- `Nome Ponto Medição`
- `System / Group`
- `Fluido`
- `Tecnologia`
- `CV_Tag_SistConectado`
- `CV_SistConectadoName`

Essa base deve enriquecer o resultado, mostrando o FC e a TAG com contexto operacional mais legível.

## Destaques

O topo da comparação deve priorizar:

- alteração de densidade
- alteração de cromatografia / GC
- mudança de pulse mode
- overrides
- alteração feita por usuário
- alteração feita por CommDrivers
- falha de login
- eventos de processo relevantes

## Implementação

### Backend

- enriquecer parser de configuração para preservar contexto de TAG
- manter upload unitário existente
- permitir fluxo de dois uploads no frontend usando o endpoint atual duas vezes
- criar resposta de comparação com agrupamento por FC/TAG

### Frontend

- adicionar segundo upload
- mostrar sugestão de pareamento por FC
- abrir comparação confirmada pelo usuário
- reorganizar resultado em `FC -> TAG -> parâmetros`
- adicionar CRUD da base de mapeamento em configurações

## Critérios de pronto

- usuário consegue carregar dois arquivos de uma vez
- aplicação sugere comparação por FC
- usuário confirma a comparação
- resultado mostra resumo por FC com TAGs identificadas
- parâmetros da mesma TAG são comparados entre dias
- referências aparecem no resultado
- base de mapeamento pode ser criada, editada e excluída
