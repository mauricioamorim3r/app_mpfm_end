# Regra de Identificação Temporal e Sobrescrita para PDFs e TXTs

Data: 2026-03-29  
Status: Draft aprovado para revisão do usuário

## Objetivo

Ajustar a lógica de ingestão da aplicação para que a identificação do dia e da janela de medição passe a usar o conteúdo interno dos arquivos, e não mais o nome do arquivo, como fonte primária de verdade.

O objetivo operacional é:

- classificar corretamente o dia de produção dos PDFs `daily`
- classificar corretamente a janela horária dos PDFs `hourly`
- classificar corretamente o dia operacional dos arquivos `TXT` do separador
- impedir que nomes de arquivo induzam uma data/hora errada
- redefinir a regra de duplicidade e sobrescrita com base na identidade real da medição

## Escopo

Entram nesta fase:

- extração de `report_start` e `report_end` de PDFs `daily`
- extração de `report_start` e `report_end` de PDFs `hourly`
- extração de `report_start` e `report_end` de arquivos `TXT`
- cálculo de `production_day` com base no início da janela
- nova identidade operacional para deduplicação
- nova regra de sobrescrita por medição mais recente
- logs de `ignorado por conteúdo idêntico` e `sobrescrito`

Ficam fora desta fase:

- migração retroativa completa de toda a base histórica
- reconstrução automática de runs antigos
- revisão de regras visuais da UI além de histórico e logs de ingestão

## Princípio Operacional

Para PDFs e TXTs, o nome do arquivo deixa de ser a fonte de verdade temporal.

A fonte de verdade passa a ser o período interno descrito no conteúdo do arquivo.

O nome do arquivo continua útil como metadado de rastreabilidade, mas não pode definir sozinho:

- o dia operacional
- a hora operacional
- a janela de medição

## Abordagem Escolhida

Foi escolhida a abordagem de **período interno do arquivo como fonte soberana da classificação temporal**, com fallback controlado apenas quando a leitura do conteúdo falhar.

Motivos:

- reflete o processo real de medição
- elimina classificações erradas causadas por nomes de arquivo
- cobre corretamente o fechamento do dia na virada `23:00 -> 00:00`
- atende tanto MPFM quanto separador

## Regras para PDFs

### PDFs `daily`

Fonte de verdade:

- trecho: `Daily Report from <start> to <end>`

Campos derivados:

- `report_start = início do trecho`
- `report_end = fim do trecho`
- `production_day = data de report_start`

Exemplo:

- arquivo: `B03_MPFM_Daily-20260320-000000+0000.pdf`
- conteúdo: `Daily Report from 2026.03.19 00:00 to 2026.03.20 00:00`
- resultado:
  - `report_start = 2026-03-19 00:00`
  - `report_end = 2026-03-20 00:00`
  - `production_day = 2026-03-19`

### PDFs `hourly`

Fonte de verdade:

- trecho: `Hourly Report from <start> to <end>`

Campos derivados:

- `report_start = início do trecho`
- `report_end = fim do trecho`
- `production_day = data de report_start`

Exemplo:

- arquivo: `B03_MPFM_Hourly-20260320-000000+0000.pdf`
- conteúdo: `Hourly Report from 2026.03.19 23:00 to 2026.03.20 00:00`
- resultado:
  - `report_start = 2026-03-19 23:00`
  - `report_end = 2026-03-20 00:00`
  - `production_day = 2026-03-19`

## Regras para TXTs

Os arquivos TXT do separador têm duas variantes de cabeçalho:

- `Start / End`
- `Period start / Period end`

Fonte de verdade:

- `Start` ou `Period start`
- `End` ou `Period end`

Campos derivados:

- `report_start = Start ou Period start`
- `report_end = End ou Period end`
- `production_day = data de report_start`

Exemplos:

- `20FT0247`
  - `Start 12/03/26 00:00:00`
  - `End 13/03/26 00:00:00`
  - `production_day = 2026-03-12`
- `20FT0244`
  - `Period start 12/03/26 00:00:00`
  - `Period end 13/03/26 00:00:00`
  - `production_day = 2026-03-12`

## Fechamento do Dia

Para um dia operacional `D`:

- o `daily` correto cobre `D 00:00 -> D+1 00:00`
- os `24 hourly` corretos cobrem:
  - `D 00:00 -> D 01:00`
  - ...
  - `D 23:00 -> D+1 00:00`

Isso significa que um arquivo com nome aparentemente do dia seguinte pode pertencer ao fechamento do dia anterior, desde que o `report_start` esteja dentro do dia anterior.

## Identidade Operacional da Medição

O sistema deve passar a identificar o arquivo por sua medição real, e não pelo nome.

### Para PDFs MPFM

Chave operacional:

- `bank`
- `tag`
- `report_kind`
- `report_start`
- `report_end`

Onde:

- `report_kind = daily` ou `hourly`

### Para TXTs SEP

Chave operacional:

- `meter_id`
- `report_start`
- `report_end`

## Regra de Duplicidade e Sobrescrita

### Caso 1: mesmo nome e mesmo conteúdo

Resultado:

- ignorar
- registrar log de conteúdo idêntico

### Caso 2: nome igual ou diferente, mas mesma identidade operacional

Resultado:

- sobrescrever a medição anterior pela mais recente inserida
- marcar a anterior como substituída
- registrar log de sobrescrita

### Caso 3: nome igual, conteúdo diferente e identidade operacional diferente

Resultado:

- aceitar como medição distinta

## Persistência

Novos metadados recomendados em `files_imported` e/ou estrutura equivalente:

- `report_start`
- `report_end`
- `production_day`
- `identity_key`
- `time_source`
- `superseded_by_file_id`
- `superseded_at`

Onde:

- `time_source = content` quando a data/hora vier do arquivo
- `time_source = filename_fallback` apenas se a leitura do conteúdo falhar

## Fallback de Segurança

Se a aplicação não conseguir ler o período interno:

- não deve confiar silenciosamente no nome
- deve registrar que usou fallback
- deve deixar a operação rastreável no log

Se a leitura estiver ambígua ou incompleta, a aplicação deve preferir marcar o arquivo como excepcional, e não classificá-lo com alta confiança usando só o nome.

## Impacto na UI

O histórico e os logs devem passar a mostrar:

- `dia operacional`
- `janela do relatório`
- `sobrescrito`
- `ignorado por conteúdo idêntico`
- `origem temporal = conteúdo ou fallback`

Isso ajuda o usuário a entender por que um arquivo com timestamp aparente de um dia foi associado a outro dia operacional.

## Ordem Recomendada de Implementação

1. parser temporal de PDFs `daily`
2. parser temporal de PDFs `hourly`
3. parser temporal de TXTs
4. cálculo unificado de `production_day`
5. nova identidade operacional
6. regra de sobrescrita
7. persistência dos novos metadados
8. ajustes de histórico/UI

## Critério de Aceite

O trabalho estará correto quando:

- PDFs `daily` forem classificados pelo início de `Daily Report from`
- PDFs `hourly` forem classificados pelo início de `Hourly Report from`
- TXTs forem classificados por `Start` ou `Period start`
- nomes de arquivo deixarem de decidir sozinhos o dia/hora da medição
- duplicidade e sobrescrita passarem a operar por identidade real da medição
- a aplicação registrar claramente quando um arquivo foi ignorado, sobrescrito ou classificado por fallback
