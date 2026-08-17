# Relatório de revisão e correções — 08/08/2026

## Resultado

O pacote foi revisado no fluxo completo: descoberta e leitura de PDF/TXT, coleta PI, geração dos dois Excel, dashboards HTML, PETEC, automação de e-mail/ZIP e XML042.

## Correções aplicadas

- O par PE‑02 × Riser P2 foi corrigido para `18FT0506 × 13FT0217`.
- A plausibilidade deixou de misturar medianas Daily e Hourly, eliminando falsos spikes nos totais diários.
- Todos os desvios usam `(MPFM corrigido − referência) / referência × 100`; denominadores abaixo de 0,1 t são suprimidos.
- A comparação livre MPFM × SEP identifica explicitamente se a rota é oficial/alinhada ou apenas diagnóstica.
- O CEP do HTML passou a carregar o mês completo correspondente à janela escolhida e permite filtrar mês, par e HC/Total.
- O XML042 ganhou registro SQLite persistente, chave única data + código ANP do poço e log de tentativas bloqueadas. Não existe mais sobrescrita.
- Duplicidade de dia + poço na fonte XML agora bloqueia a emissão em vez de manter silenciosamente a última linha.

- Comparações Subsea × Topside agora usam banco **e instrumento oficial**. O instrumento `18FT1706` do B05 não é mais somado ao `18FT1506` na comparação PE-04 × Riser P5.
- A verificação incremental exige todos os instrumentos esperados por dia, evitando considerar o B05 completo quando apenas uma de suas seções foi consolidada.
- Dashboard de um único dia usa Hourly quando disponível e faz fallback para Daily quando não houver registros horários.
- Cada HTML carrega as abas de origem uma única vez e reutiliza os mesmos dados na geração e na validação.
- As abas automáticas do Excel standalone são gravadas no mesmo ciclo de escrita, reduzindo reaberturas do arquivo.
- A automação de e-mail recebe o destino correto dos TXT do separador e possui timeout configurável (`BASE_UNICA_EMAIL_TIMEOUT_SECONDS`, padrão 900 s).
- Extrações ZIP bloqueiam caminhos inseguros e impõem limites configuráveis de quantidade e tamanho descompactado.
- PETEC exige uma origem SEP válida, salvo uso explícito de `--allow-missing-sep`, e aceita filtros `--bank`, `--tag` e `--instrument`.
- Ausência de PDF Daily ou ausência total de linhas passa a encerrar o processo com código diferente de zero.

## XML042 e produção zerada

- Produção oficial com óleo, gás e água iguais a zero continua válida e gera XML com `IND_VALIDO=S`.
- O manifesto registra `PRODUCAO_ZERADA_OFICIAL` ou `PRODUCAO_POSITIVA_OFICIAL`.
- Volumes ausentes ou negativos são rejeitados e registrados no relatório de rejeições.
- A coluna `IsOfficial` é obrigatória quando `require_is_official=true`.
- O XML é validado estruturalmente e numericamente antes da gravação. Esta validação não substitui uma validação externa contra o arquivo `042.xsd` oficial.

## Testes incluídos

Execute na raiz do pacote:

```bash
python -m unittest discover -s tests -v
```

Os testes cobrem o isolamento dos instrumentos do B05, completude incremental, fallback Daily do HTML, XML de produção zerada e rejeição de volume negativo.

## Recomendação para volumes históricos maiores

O pacote continua usando Excel como arquivo oficial e fonte de apresentação. Se o histórico crescer de forma significativa, a evolução recomendada é manter a camada de processamento em Parquet/DuckDB e exportar Excel/HTML somente ao final. Isso reduz o custo de reabrir e regravar `BASE_UNICA_TOTAL.xlsx`, sem alterar os entregáveis operacionais.
