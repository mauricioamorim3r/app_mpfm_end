# XML 002 - pontos de medicao para gas linear

Fonte base: `referencias_doc/Manual XML 002.pdf` e exemplo `referencias_doc/002_04028583_20260415001000_38480.xml`.

## Finalidade

O XML 002 representa a leitura de configuracao e producao de pontos de medicao de gas linear. Nos exemplos do projeto, este tipo cobre medidores lineares como gas de flare com tecnologia ultrassonica de queima.

## Nomenclatura do arquivo

Formato obrigatorio:

```text
002_bbbbbbbb_cccccccccccccc.ddd
```

| Parte | Regra |
| --- | --- |
| `002` | Codigo fixo do arquivo. Nao deve ser alterado. |
| `bbbbbbbb` | 8 primeiros digitos do CNPJ da operadora. |
| `cccccccccccccc` | Data/hora de geracao no formato `AAAAMMDDHHmmSS`. |
| `ddd` | `xml` ou `zip`. |

Exemplo: `002_04028583_20260415001000_38480.xml`.

Observacao operacional: para analise de periodo na aplicacao, usar os campos internos (`DHA_COLETA`, `DHA_INICIO_PERIODO_MEDICAO`, `DHA_FIM_PERIODO_MEDICAO`), nao a data do nome do arquivo.

## Regras gerais de formato

| Item | Regra |
| --- | --- |
| Encoding | O exemplo oficial usa `<?xml version="1.0" encoding="iso-8859-1"?>`. |
| Raiz | Elemento raiz deve ser `<a002>`. |
| Estrutura | Manter estrutura inalterada mesmo quando a informacao nao for pertinente. |
| Campos vazios | Usar elemento vazio/self-closing quando aplicavel. |
| Numeros racionais | Usar virgula decimal, sem separador de milhar. |
| Datas | `DATA_HORA` no formato `DD/MM/AAAA HH:mm:SS`. |
| SIM_NAO | Usar `S` ou `N`. |
| Texto | Respeitar tamanho maximo definido por campo. |
| Case dos elementos | Manter tags em maiusculas conforme manual. |

## Natureza dos campos

| Natureza | Regra |
| --- | --- |
| `ANO_MES` | `AAAAMM`, sem separadores. |
| `TEXTO` | Texto livre ate o tamanho maximo. |
| `NATURAL` | Inteiro nao negativo. |
| `INTEIRO` | Inteiro com ou sem sinal. |
| `DATA` | `DD/MM/AAAA`. |
| `DATA_HORA` | `DD/MM/AAAA HH:mm:SS`. |
| `RACIONAL` | Numero com virgula decimal. |
| `SIM_NAO` | `S` ou `N`. |

## Estrutura hierarquica

```xml
<a002>
  <LISTA_DADOS_BASICOS>
    <DADOS_BASICOS NUM_SERIE_ELEMENTO_PRIMARIO="..." COD_INSTALACAO="..." COD_TAG_PONTO_MEDICAO="...">
      <LISTA_CONFIGURACAO_CV><CONFIGURACAO_CV>...</CONFIGURACAO_CV></LISTA_CONFIGURACAO_CV>
      <LISTA_ELEMENTO_PRIMARIO><ELEMENTO_PRIMARIO>...</ELEMENTO_PRIMARIO></LISTA_ELEMENTO_PRIMARIO>
      <LISTA_INSTRUMENTO_PRESSAO><INSTRUMENTO_PRESSAO>...</INSTRUMENTO_PRESSAO></LISTA_INSTRUMENTO_PRESSAO>
      <LISTA_INSTRUMENTO_TEMPERATURA><INSTRUMENTO_TEMPERATURA>...</INSTRUMENTO_TEMPERATURA></LISTA_INSTRUMENTO_TEMPERATURA>
      <LISTA_PRODUCAO><PRODUCAO>...</PRODUCAO></LISTA_PRODUCAO>
    </DADOS_BASICOS>
  </LISTA_DADOS_BASICOS>
</a002>
```

## Cardinalidade dos grupos

| Grupo | Minimo | Maximo | Obrigatorio | Observacao |
| --- | ---: | ---: | --- | --- |
| `DADOS_BASICOS` | 1 | Ilimitado | Sim | Um registro por ponto de gas linear. |
| `CONFIGURACAO_CV` | 1 | 1 | Sim | Exatamente um por ponto. |
| `ELEMENTO_PRIMARIO` | 1 | 1 | Sim | Exatamente um por ponto. |
| `INSTRUMENTO_PRESSAO` | 1 | Ilimitado | Sim | Informar todos os instrumentos de pressao. |
| `INSTRUMENTO_TEMPERATURA` | 1 | Ilimitado | Sim | Informar todos os instrumentos de temperatura. |
| `PRODUCAO` | 1 | 1 | Sim | Exatamente um por periodo. |

## Campos obrigatorios por grupo

### `DADOS_BASICOS` atributos

| Campo | Natureza | Tamanho | Obrigatorio | Regra |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE_ELEMENTO_PRIMARIO` | TEXTO | 30 | Sim | Numero de serie do instrumento/elemento primario usado no cadastro. |
| `COD_INSTALACAO` | NATURAL | 10 | Sim | Codigo da instalacao. |
| `COD_TAG_PONTO_MEDICAO` | TEXTO | 20 | Sim | TAG do ponto conforme cadastro SFP. |

### `CONFIGURACAO_CV`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE_COMPUTADOR_VAZAO` | TEXTO | 30 | Sim | Numero de serie do computador de vazao. |
| `DHA_COLETA` | DATA_HORA | 19 | Sim | Data/hora da configuracao. |
| `MED_TEMPERATURA` | RACIONAL | (3,2) | Sim | Celsius. |
| `MED_PRESSAO_ATMSA` | RACIONAL | (3,3) | Sim | kPa. |
| `MED_PRESSAO_RFRNA` | RACIONAL | (3,3) | Sim | kPa. |
| `MED_DENSIDADE_RELATIVA` | RACIONAL | (2,8) | Sim | Densidade relativa usada no calculo. |
| `DSC_NORMA_UTILIZADA_CALCULO` | TEXTO | 50 | Nao | Norma de calculo, exemplo `AGA-9 - AGA-8 1994 Detailes Analysis`. |
| `PCT_CROMATOGRAFIA_NITROGENIO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_CO2` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_METANO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_ETANO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_PROPANO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_N_BUTANO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_I_BUTANO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_N_PENTANO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_I_PENTANO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_HEXANO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_HEPTANO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_OCTANO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_NONANO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_DECANO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_H2S` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_AGUA` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_HELIO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_OXIGENIO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_CO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_HIDROGENIO` | RACIONAL | (3,6) | Nao | Mol. |
| `PCT_CROMATOGRAFIA_ARGONIO` | RACIONAL | (3,6) | Nao | Mol. |
| `DSC_VERSAO_SOFTWARE` | TEXTO | 30 | Sim | Versao do software. |

### `ELEMENTO_PRIMARIO`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `ICE_METER_FACTOR_1` | RACIONAL | (1,5) | Sim | Meter factor principal ou unico. |
| `ICE_METER_FACTOR_2` a `ICE_METER_FACTOR_15` | RACIONAL | (1,5) | Nao | Meter factors adicionais. |
| `QTD_PULSOS_METER_FACTOR_1` a `QTD_PULSOS_METER_FACTOR_15` | RACIONAL | (8,2) | Nao | Hz. |
| `ICE_K_FACTOR_1` | RACIONAL | (8,2) | Sim | Pulso/m3, K factor principal ou unico. |
| `ICE_K_FACTOR_2` a `ICE_K_FACTOR_15` | RACIONAL | (8,2) | Nao | K factors adicionais. |
| `QTD_PULSOS_K_FACTOR_1` a `QTD_PULSOS_K_FACTOR_15` | RACIONAL | (8,2) | Nao | Hz. |
| `ICE_CUTOFF` | RACIONAL | (6,3) | Sim | 10^3 m3/h, limite inferior de computo. |
| `ICE_LIMITE_SPRR_ALARME` | RACIONAL | (6,3) | Sim | 10^3 m3/h, limite superior de vazao. |
| `ICE_LIMITE_INFRR_ALARME` | RACIONAL | (6,3) | Sim | 10^3 m3/h, limite inferior de vazao. |
| `IND_HABILITACAO_ALARME` | SIM_NAO | 1 | Sim | `S` ou `N`. |

### `INSTRUMENTO_PRESSAO`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE` | TEXTO | 30 | Sim | Numero de serie. |
| `MED_PRSO_LIMITE_SPRR_ALRME` | RACIONAL | (6,3) | Sim | kPa, limite superior. |
| `MED_PRSO_LMTE_INFRR_ALRME` | RACIONAL | (6,3) | Sim | kPa, limite inferior. |
| `IND_HABILITACAO_ALARME` | SIM_NAO | 1 | Sim | `S` ou `N`. |
| `MED_PRSO_ADOTADA_FALHA` | RACIONAL | (6,3) | Sim | kPa, valor adotado em falha. |
| `DSC_ESTADO_INSNO_CASO_FALHA` | TEXTO | 50 | Sim | Acao em falha. |
| `IND_TIPO_PRESSAO_CONSIDERADA` | TEXTO | 1 | Sim | `A` absoluta ou `M` manometrica. |

### `INSTRUMENTO_TEMPERATURA`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE` | TEXTO | 30 | Sim | Numero de serie. |
| `MED_TMPTA_SPRR_ALARME` | RACIONAL | (3,2) | Sim | Celsius, limite superior. |
| `MED_TMPTA_INFRR_ALRME` | RACIONAL | (3,2) | Sim | Celsius, limite inferior. |
| `IND_HABILITACAO_ALARME` | SIM_NAO | 1 | Sim | `S` ou `N`. |
| `MED_TMPTA_ADTTA_FALHA` | RACIONAL | (3,2) | Sim | Celsius, valor adotado em falha. |
| `DSC_ESTADO_INSTRUMENTO_FALHA` | TEXTO | 50 | Sim | Acao em falha. |

### `PRODUCAO`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `DHA_INICIO_PERIODO_MEDICAO` | DATA_HORA | 19 | Sim | Inicio do periodo. |
| `DHA_FIM_PERIODO_MEDICAO` | DATA_HORA | 19 | Sim | Fim do periodo. |
| `ICE_DENSIDADE_RELATIVA` | RACIONAL | (2,8) | Nao | Media ponderada da densidade relativa. |
| `MED_PRESSAO_ESTATICA` | RACIONAL | (6,3) | Sim | kPa. |
| `MED_TEMPERATURA` | RACIONAL | (3,2) | Sim | Celsius. |
| `PRZ_DURACAO_FLUXO_EFETIVO` | RACIONAL | (4,4) | Sim | Minutos. |
| `MED_BRUTO_MOVIMENTADO` | RACIONAL | (6,5) | Sim | 10^3 m3, volume bruto movimentado. |
| `MED_CORRIGIDO_MVMDO` | RACIONAL | (6,5) | Sim | 10^3 m3, volume corrigido movimentado. |

## Regras de validacao SGMed

- Validar raiz `a002` e codigo de arquivo `002`.
- Correlacionar `COD_TAG_PONTO_MEDICAO` com o cadastro de pontos de medicao.
- Correlacionar `NUM_SERIE_COMPUTADOR_VAZAO` com o CV cadastrado.
- Verificar composicao cromatografica quando presente; ela deve usar virgula decimal e campos `PCT_CROMATOGRAFIA_*`.
- Confirmar existencia de `CONFIGURACAO_CV`, `ELEMENTO_PRIMARIO`, `INSTRUMENTO_PRESSAO`, `INSTRUMENTO_TEMPERATURA` e `PRODUCAO` por ponto.
- Campos criticos: densidade relativa, norma de calculo, composicao cromatografica, meter/K factors, cutoff, limites de vazao, limites de pressao/temperatura, valores adotados em falha e volumes produzidos.
