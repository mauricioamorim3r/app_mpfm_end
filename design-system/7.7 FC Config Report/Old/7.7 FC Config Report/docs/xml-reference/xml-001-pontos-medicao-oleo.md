# XML 001 - pontos de medicao para oleo

Fonte base: `referencias_doc/Manual XML 001.pdf` e exemplo `referencias_doc/001_04028583_20260415001000_38480.xml`.

## Finalidade

O XML 001 representa a leitura de configuracao e producao de pontos de medicao de oleo em uma instalacao. Cada registro de `DADOS_BASICOS` corresponde a um ponto de medicao e deve permitir correlacao com o cadastro ANP/SFP e com o cadastro interno SGMed.

## Nomenclatura do arquivo

Formato obrigatorio:

```text
001_bbbbbbbb_cccccccccccccc.ddd
```

Onde:

| Parte | Regra |
| --- | --- |
| `001` | Codigo fixo do arquivo. Nao deve ser alterado. |
| `bbbbbbbb` | 8 primeiros digitos do CNPJ da operadora. |
| `cccccccccccccc` | Data/hora de geracao no formato `AAAAMMDDHHmmSS`. |
| `ddd` | `xml` para arquivo descompactado ou `zip` para arquivo compactado. |

Exemplo: `001_04028583_20260415001000_38480.xml`.

Observacao operacional: para analise de periodo na aplicacao, usar os campos internos do XML (`DHA_COLETA`, `DHA_INICIO_PERIODO_MEDICAO`, `DHA_FIM_PERIODO_MEDICAO`), nao a data do nome do arquivo.

## Regras gerais de formato

| Item | Regra |
| --- | --- |
| Encoding | O exemplo oficial usa `<?xml version="1.0" encoding="iso-8859-1"?>`. |
| Raiz | Elemento raiz deve ser `<a001>`. |
| Estrutura | A estrutura deve ser mantida inalterada mesmo quando uma informacao nao for pertinente. |
| Campos vazios | Campos nao pertinentes podem vir vazios, como `<MED_DENSIDADE_RELATIVA/>`. |
| Numeros racionais | Usar virgula como separador decimal. Nao usar ponto como separador de milhar. |
| Datas | `DATA_HORA` no formato `DD/MM/AAAA HH:mm:SS`, com 19 caracteres. |
| SIM_NAO | Usar `S` para sim e `N` para nao. |
| Texto | Respeitar tamanho maximo do manual para cada campo. |
| Case dos elementos | Manter nomes de tags em maiusculas conforme manual. |

## Natureza dos campos

| Natureza | Regra |
| --- | --- |
| `ANO_MES` | Ano e mes no formato `AAAAMM`, sem separadores. |
| `TEXTO` | Texto livre ate o tamanho maximo definido. |
| `NATURAL` | Inteiro nao negativo. |
| `INTEIRO` | Inteiro com ou sem sinal. |
| `DATA` | `DD/MM/AAAA`. |
| `DATA_HORA` | `DD/MM/AAAA HH:mm:SS`. |
| `RACIONAL` | Parte inteira e decimal separadas por virgula. |
| `SIM_NAO` | `S` ou `N`. |

## Estrutura hierarquica

```xml
<a001>
  <LISTA_DADOS_BASICOS>
    <DADOS_BASICOS NUM_SERIE_ELEMENTO_PRIMARIO="..." COD_INSTALACAO="..." COD_TAG_PONTO_MEDICAO="...">
      <LISTA_CONFIGURACAO_CV><CONFIGURACAO_CV>...</CONFIGURACAO_CV></LISTA_CONFIGURACAO_CV>
      <LISTA_ELEMENTO_PRIMARIO><ELEMENTO_PRIMARIO>...</ELEMENTO_PRIMARIO></LISTA_ELEMENTO_PRIMARIO>
      <LISTA_INSTRUMENTO_PRESSAO><INSTRUMENTO_PRESSAO>...</INSTRUMENTO_PRESSAO></LISTA_INSTRUMENTO_PRESSAO>
      <LISTA_INSTRUMENTO_TEMPERATURA><INSTRUMENTO_TEMPERATURA>...</INSTRUMENTO_TEMPERATURA></LISTA_INSTRUMENTO_TEMPERATURA>
      <LISTA_ANALISADOR_DENSIDADE><ANALISADOR_DENSIDADE>...</ANALISADOR_DENSIDADE></LISTA_ANALISADOR_DENSIDADE>
      <LISTA_ANALISADOR_BSW><ANALISADOR_BSW>...</ANALISADOR_BSW></LISTA_ANALISADOR_BSW>
      <LISTA_PRODUCAO><PRODUCAO>...</PRODUCAO></LISTA_PRODUCAO>
    </DADOS_BASICOS>
  </LISTA_DADOS_BASICOS>
</a001>
```

## Cardinalidade dos grupos

| Grupo | Minimo | Maximo | Obrigatorio | Observacao |
| --- | ---: | ---: | --- | --- |
| `DADOS_BASICOS` | 1 | Ilimitado | Sim | Um registro por ponto de medicao. |
| `CONFIGURACAO_CV` | 1 | 1 | Sim | Exatamente um por ponto. |
| `ELEMENTO_PRIMARIO` | 1 | 1 | Sim | Exatamente um por ponto. |
| `INSTRUMENTO_PRESSAO` | 1 | Ilimitado | Sim | Informar todos os instrumentos de pressao existentes. |
| `INSTRUMENTO_TEMPERATURA` | 1 | Ilimitado | Sim | Informar todos os instrumentos de temperatura existentes. |
| `ANALISADOR_DENSIDADE` | 0 | Ilimitado | Nao | Somente se existir analisador instalado. |
| `ANALISADOR_BSW` | 0 | Ilimitado | Nao | Somente se existir analisador BSW instalado. |
| `PRODUCAO` | 1 | 1 | Sim | Exatamente um registro por periodo. |

## Campos obrigatorios por grupo

### `DADOS_BASICOS` atributos

| Campo | Natureza | Tamanho | Obrigatorio | Regra |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE_ELEMENTO_PRIMARIO` | TEXTO | 30 | Sim | Numero de serie do instrumento/elemento primario usado no cadastro do ponto. |
| `COD_INSTALACAO` | NATURAL | 10 | Sim | Codigo da instalacao. |
| `COD_TAG_PONTO_MEDICAO` | TEXTO | 20 | Sim | TAG do ponto de medicao conforme cadastro SFP. |

### `CONFIGURACAO_CV`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE_COMPUTADOR_VAZAO` | TEXTO | 30 | Sim | Numero de serie do computador de vazao. |
| `DHA_COLETA` | DATA_HORA | 19 | Sim | Momento de registro da configuracao. |
| `MED_TEMPERATURA` | RACIONAL | (3,2) | Sim | Celsius. |
| `MED_PRESSAO_ATMSA` | RACIONAL | (3,3) | Sim | kPa. |
| `MED_PRESSAO_RFRNA` | RACIONAL | (3,3) | Sim | kPa. |
| `MED_DENSIDADE_RELATIVA` | RACIONAL | (2,8) | Nao | Densidade relativa do oleo. |
| `DSC_VERSAO_SOFTWARE` | TEXTO | 30 | Sim | Versao do software do CV. |

### `ELEMENTO_PRIMARIO`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `ICE_METER_FACTOR_1` | RACIONAL | (1,5) | Sim | Meter factor principal ou unico. |
| `ICE_METER_FACTOR_2` a `ICE_METER_FACTOR_15` | RACIONAL | (1,5) | Nao | Meter factors adicionais. |
| `QTD_PULSOS_METER_FACTOR_1` a `QTD_PULSOS_METER_FACTOR_15` | RACIONAL | (8,2) | Nao | Hz, frequencia associada ao meter factor. |
| `ICE_K_FACTOR_1` | RACIONAL | (8,2) | Sim | Pulso/m3, K factor principal ou unico. |
| `ICE_K_FACTOR_2` a `ICE_K_FACTOR_15` | RACIONAL | (8,2) | Nao | K factors adicionais. |
| `QTD_PULSOS_K_FACTOR_1` a `QTD_PULSOS_K_FACTOR_15` | RACIONAL | (8,2) | Nao | Hz, frequencia associada ao K factor. |
| `ICE_CUTOFF` | RACIONAL | (6,2) | Sim | m3/h, limite inferior de computo de volumes. |
| `ICE_LIMITE_SPRR_ALARME` | RACIONAL | (6,2) | Sim | m3/h, limite superior de alarme de vazao. |
| `ICE_LIMITE_INFRR_ALARME` | RACIONAL | (6,2) | Sim | m3/h, limite inferior de alarme de vazao. |
| `IND_HABILITACAO_ALARME` | SIM_NAO | 1 | Sim | `S` ou `N`. |

### `INSTRUMENTO_PRESSAO`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE` | TEXTO | 30 | Sim | Numero de serie do instrumento. |
| `MED_PRSO_LIMITE_SPRR_ALRME` | RACIONAL | (6,3) | Sim | kPa, limite superior de alarme. |
| `MED_PRSO_LMTE_INFRR_ALRME` | RACIONAL | (6,3) | Sim | kPa, limite inferior de alarme. |
| `IND_HABILITACAO_ALARME` | SIM_NAO | 1 | Sim | `S` ou `N`. |
| `MED_PRSO_ADOTADA_FALHA` | RACIONAL | (6,3) | Sim | kPa, valor adotado em falha. |
| `DSC_ESTADO_INSNO_CASO_FALHA` | TEXTO | 50 | Sim | Acao em falha, exemplo `Override value`. |
| `IND_TIPO_PRESSAO_CONSIDERADA` | TEXTO | 1 | Sim | `A` absoluta ou `M` manometrica. |

### `INSTRUMENTO_TEMPERATURA`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE` | TEXTO | 30 | Sim | Numero de serie do instrumento. |
| `MED_TMPTA_SPRR_ALARME` | RACIONAL | (3,2) | Sim | Celsius, limite superior. |
| `MED_TMPTA_INFRR_ALRME` | RACIONAL | (3,2) | Sim | Celsius, limite inferior. |
| `IND_HABILITACAO_ALARME` | SIM_NAO | 1 | Sim | `S` ou `N`. |
| `MED_TMPTA_ADTTA_FALHA` | RACIONAL | (3,2) | Sim | Celsius, valor adotado em falha. |
| `DSC_ESTADO_INSTRUMENTO_FALHA` | TEXTO | 50 | Sim | Acao em falha. |

### `ANALISADOR_DENSIDADE` e `ANALISADOR_BSW`

Campos aplicaveis quando o instrumento existir:

| Campo | Natureza | Tamanho | Obrigatorio | Observacao |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE` | TEXTO | 30 | Sim | Numero de serie. |
| `PCT_LIMITE_SUPERIOR` | RACIONAL | (3,3) | Nao | Limite superior percentual. |
| `PCT_LIMITE_INFERIOR` | RACIONAL | (3,3) | Nao | Limite inferior percentual. |
| `IND_HABILITACAO_ALARME` | SIM_NAO | 1 | Nao | `S` ou `N`. |
| `PCT_ADOTADO_CASO_FALHA` | RACIONAL | (3,3) | Nao | Percentual adotado em falha. |
| `DSC_ESTADO_INSTRUMENTO_FALHA` | TEXTO | 50 | Nao | Acao em falha. |

### `PRODUCAO`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `DHA_INICIO_PERIODO_MEDICAO` | DATA_HORA | 19 | Sim | Inicio do periodo de medicao. |
| `DHA_FIM_PERIODO_MEDICAO` | DATA_HORA | 19 | Sim | Fim do periodo de medicao. |
| `ICE_DENSIDADADE_RELATIVA` | RACIONAL | (2,8) | Nao | Grafia observada no XML 001 de exemplo: `DENSIDADADE`. |
| `ICE_CORRECAO_BSW` | RACIONAL | (2,8) | Nao | Fator medio de correcao de BSW. |
| `ICE_CORRECAO_PRESSAO_LIQUIDO` | RACIONAL | (2,8) | Sim | CPL. |
| `ICE_CRRCO_TEMPERATURA_LIQUIDO` | RACIONAL | (2,8) | Sim | CTL. |
| `MED_PRESSAO_ESTATICA` | RACIONAL | (6,6) | Sim | kPa. |
| `MED_TMPTA_FLUIDO` | RACIONAL | (3,5) | Sim | Celsius. |
| `MED_VOLUME_BRTO_CRRGO_MVMDO` | RACIONAL | (6,5) | Sim | m3, volume bruto corrigido movimentado. |
| `MED_VOLUME_BRUTO_MVMDO` | RACIONAL | (6,5) | Sim | m3, volume bruto em operacao. |
| `MED_VOLUME_LIQUIDO_MVMDO` | RACIONAL | (6,5) | Sim | m3, volume liquido movimentado. |
| `MED_VOLUME_TTLZO_FIM_PRDO` | RACIONAL | (10,2) | Sim | m3, totalizador no fim do periodo. |
| `MED_VOLUME_TTLZO_INCO_PRDO` | RACIONAL | (10,2) | Sim | m3, totalizador no inicio do periodo. |

## Regras de validacao SGMed

- Validar raiz `a001` e codigo de arquivo `001`.
- Correlacionar `COD_TAG_PONTO_MEDICAO` com o cadastro de pontos de medicao.
- Correlacionar `NUM_SERIE_COMPUTADOR_VAZAO` com o CV cadastrado.
- Validar que cada `DADOS_BASICOS` tenha `CONFIGURACAO_CV`, `ELEMENTO_PRIMARIO`, `INSTRUMENTO_PRESSAO`, `INSTRUMENTO_TEMPERATURA` e `PRODUCAO`.
- Manter campos vazios como informacao presente mas sem valor, nao como campo inexistente.
- Para comparacao historica, usar `DHA_COLETA` e o periodo `DHA_INICIO_PERIODO_MEDICAO`/`DHA_FIM_PERIODO_MEDICAO`.
- Campos metrologicos criticos: meter factors, K factors, cutoff, limites de alarme, valores adotados em falha, densidade, CPL, CTL e totalizadores.
