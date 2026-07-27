# XML 003 - pontos de medicao para gas diferencial

Fonte base: `referencias_doc/Manual XML 003.pdf` e exemplo `referencias_doc/003_04028583_20260415001000_38480.xml`.

## Finalidade

O XML 003 representa a leitura de configuracao e producao de pontos de medicao de gas diferencial. Nos exemplos do projeto, este XML cobre medidores por placa de orificio e cone, como `45FT0555`, `26FT1501` e outros pontos de gas diferencial.

## Nomenclatura do arquivo

Formato obrigatorio:

```text
003_bbbbbbbb_cccccccccccccc.ddd
```

| Parte | Regra |
| --- | --- |
| `003` | Codigo fixo do arquivo. Nao deve ser alterado. |
| `bbbbbbbb` | 8 primeiros digitos do CNPJ da operadora. |
| `cccccccccccccc` | Data/hora de geracao no formato `AAAAMMDDHHmmSS`. |
| `ddd` | `xml` ou `zip`. |

Exemplo: `003_04028583_20260415001000_38480.xml`.

Observacao operacional: para analise de periodo na aplicacao, usar os campos internos (`DHA_COLETA`, `DHA_INICIO_PERIODO_MEDICAO`, `DHA_FIM_PERIODO_MEDICAO`), nao a data do nome do arquivo.

## Regras gerais de formato

| Item | Regra |
| --- | --- |
| Encoding | O exemplo oficial usa `<?xml version="1.0" encoding="iso-8859-1"?>`. |
| Raiz | Elemento raiz deve ser `<a003>`. |
| Estrutura | Manter estrutura inalterada mesmo quando a informacao nao for pertinente. |
| Campos vazios | Usar elementos vazios quando aplicavel. |
| Numeros racionais | Usar virgula decimal, sem ponto como separador de milhar. |
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
<a003>
  <LISTA_DADOS_BASICOS>
    <DADOS_BASICOS NUM_SERIE_ELEMENTO_PRIMARIO="..." COD_INSTALACAO="..." COD_TAG_PONTO_MEDICAO="...">
      <LISTA_CONFIGURACAO_CV><CONFIGURACAO_CV>...</CONFIGURACAO_CV></LISTA_CONFIGURACAO_CV>
      <LISTA_ELEMENTO_PRIMARIO><ELEMENTO_PRIMARIO>...</ELEMENTO_PRIMARIO></LISTA_ELEMENTO_PRIMARIO>
      <LISTA_INSTRUMENTO_PRESSAO><INSTRUMENTO_PRESSAO>...</INSTRUMENTO_PRESSAO></LISTA_INSTRUMENTO_PRESSAO>
      <LISTA_INSTRUMENTO_TEMPERATURA><INSTRUMENTO_TEMPERATURA>...</INSTRUMENTO_TEMPERATURA></LISTA_INSTRUMENTO_TEMPERATURA>
      <LISTA_PLACA_ORIFICIO><PLACA_ORIFICIO>...</PLACA_ORIFICIO></LISTA_PLACA_ORIFICIO>
      <LISTA_INST_DIFEREN_PRESSAO_PRINCIPAL><INST_DIFEREN_PRESSAO_PRINCIPAL>...</INST_DIFEREN_PRESSAO_PRINCIPAL></LISTA_INST_DIFEREN_PRESSAO_PRINCIPAL>
      <LISTA_INST_DIFEREN_PRESSAO_ALTA><INST_DIFEREN_PRESSAO_ALTA>...</INST_DIFEREN_PRESSAO_ALTA></LISTA_INST_DIFEREN_PRESSAO_ALTA>
      <LISTA_INST_DIFEREN_PRESSAO_MEDIA><INST_DIFEREN_PRESSAO_MEDIA>...</INST_DIFEREN_PRESSAO_MEDIA></LISTA_INST_DIFEREN_PRESSAO_MEDIA>
      <LISTA_INST_DIFEREN_PRESSAO_BAIXA><INST_DIFEREN_PRESSAO_BAIXA>...</INST_DIFEREN_PRESSAO_BAIXA></LISTA_INST_DIFEREN_PRESSAO_BAIXA>
      <LISTA_PRODUCAO><PRODUCAO>...</PRODUCAO></LISTA_PRODUCAO>
    </DADOS_BASICOS>
  </LISTA_DADOS_BASICOS>
</a003>
```

## Cardinalidade dos grupos

| Grupo | Minimo | Maximo | Obrigatorio | Observacao |
| --- | ---: | ---: | --- | --- |
| `DADOS_BASICOS` | 1 | Ilimitado | Sim | Um registro por ponto de gas diferencial. |
| `CONFIGURACAO_CV` | 1 | 1 | Sim | Exatamente um por ponto. |
| `ELEMENTO_PRIMARIO` | 1 | 1 | Sim | Exatamente um por ponto. |
| `INSTRUMENTO_PRESSAO` | 1 | Ilimitado | Sim | Pressao estatica. |
| `INSTRUMENTO_TEMPERATURA` | 1 | Ilimitado | Sim | Temperatura. |
| `PLACA_ORIFICIO` | 1 | 1 | Sim | Placa/orificio ou configuracao equivalente do trecho de medicao. |
| `INST_DIFEREN_PRESSAO_PRINCIPAL` | 0 | Ilimitado | Condicional | Obrigatorio quando nao houver instrumento diferencial com extensao de faixa. |
| `INST_DIFEREN_PRESSAO_ALTA` | 0 | Ilimitado | Nao | Diferencial de pressao alta com extensao de faixa. |
| `INST_DIFEREN_PRESSAO_MEDIA` | 0 | Ilimitado | Nao | Diferencial de pressao media com extensao de faixa. |
| `INST_DIFEREN_PRESSAO_BAIXA` | 0 | Ilimitado | Nao | Diferencial de pressao baixa com extensao de faixa. |
| `PRODUCAO` | 1 | 1 | Sim | Exatamente um por periodo. |

## Campos obrigatorios por grupo

### `DADOS_BASICOS` atributos

| Campo | Natureza | Tamanho | Obrigatorio | Regra |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE_ELEMENTO_PRIMARIO` | TEXTO | 30 | Sim | Numero de serie do instrumento; no caso de placa, considerar o numero da placa. |
| `COD_INSTALACAO` | NATURAL | 10 | Sim | Codigo da instalacao. |
| `COD_TAG_PONTO_MEDICAO` | TEXTO | 20 | Sim | TAG do ponto conforme cadastro SFP. |

### `CONFIGURACAO_CV`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE_COMPUTADOR_VAZAO` | TEXTO | 30 | Sim | Identificacao do computador de vazao. |
| `DHA_COLETA` | DATA_HORA | 19 | Sim | Data/hora da configuracao. |
| `MED_TEMPERATURA` | RACIONAL | (3,2) | Sim | Celsius. |
| `MED_PRESSAO_ATMSA` | RACIONAL | (3,3) | Sim | kPa. |
| `MED_PRESSAO_RFRNA` | RACIONAL | (3,3) | Sim | kPa. |
| `MED_DENSIDADE_RELATIVA` | RACIONAL | (2,8) | Sim | Densidade relativa do gas. |
| `DSC_NORMA_UTILIZADA_CALCULO` | TEXTO | 50 | Sim | Norma de calculo, exemplo `ISO5167 - AGA-8 1994 Detailes Analysis`. |
| `PCT_CROMATOGRAFIA_NITROGENIO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_CO2` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_METANO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_ETANO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_PROPANO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_N_BUTANO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_I_BUTANO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_N_PENTANO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_I_PENTANO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_HEXANO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_HEPTANO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_OCTANO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_NONANO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_DECANO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_H2S` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_AGUA` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_HELIO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_OXIGENIO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_CO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_HIDROGENIO` | RACIONAL | (3,6) | Sim | Mol. |
| `PCT_CROMATOGRAFIA_ARGONIO` | RACIONAL | (3,6) | Sim | Mol. |
| `DSC_VERSAO_SOFTWARE` | TEXTO | 30 | Sim | Versao do software. |

### `ELEMENTO_PRIMARIO`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `ICE_LIMITE_SPRR_ALARME` | RACIONAL | (6,3) | Sim | 10^3 m3/h, limite superior de alarme. |
| `ICE_LIMITE_INFRR_ALARME` | RACIONAL | (6,3) | Sim | 10^3 m3/h, limite inferior de alarme. |
| `IND_HABILITACAO_ALARME` | SIM_NAO | 1 | Sim | `S` ou `N`. |

### `INSTRUMENTO_PRESSAO`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE` | TEXTO | 30 | Sim | Numero de serie. |
| `MED_PRSO_LIMITE_SPRR_ALRME` | RACIONAL | (6,3) | Sim | kPa, limite superior. |
| `MED_PRSO_LMTE_INFRR_ALRME` | RACIONAL | (6,3) | Sim | kPa, limite inferior. |
| `IND_HABILITACAO_ALARME` | SIM_NAO | 1 | Sim | `S` ou `N`. |
| `MED_PRSO_ADOTADA_FALHA` | RACIONAL | (6,3) | Sim | kPa, pressao adotada em falha. |
| `DSC_ESTADO_INSNO_CASO_FALHA` | TEXTO | 50 | Sim | Acao em falha. |
| `IND_TIPO_PRESSAO_CONSIDERADA` | TEXTO | 1 | Sim | `A` absoluta ou `M` manometrica. |

### `INSTRUMENTO_TEMPERATURA`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE` | TEXTO | 30 | Sim | Numero de serie. |
| `MED_TMPTA_SPRR_ALARME` | RACIONAL | (3,2) | Sim | Celsius, limite superior. |
| `MED_TMPTA_INFRR_ALRME` | RACIONAL | (3,2) | Sim | Celsius, limite inferior. |
| `IND_HABILITACAO_ALARME` | SIM_NAO | 1 | Sim | `S` ou `N`. |
| `MED_TMPTA_ADTTA_FALHA` | RACIONAL | (3,2) | Sim | Celsius, temperatura adotada em falha. |
| `DSC_ESTADO_INSTRUMENTO_FALHA` | TEXTO | 50 | Sim | Acao em falha. |

### `PLACA_ORIFICIO`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `MED_DIAMETRO_REFERENCIA` | RACIONAL | (4,3) | Sim | mm, diametro de referencia do orificio. |
| `MED_TEMPERATURA_RFRNA` | RACIONAL | (3,2) | Sim | Celsius, temperatura de referencia. |
| `DSC_MATERIAL_CONTRUCAO_PLACA` | TEXTO | 50 | Sim | Material da placa. |
| `MED_DMTRO_INTRO_TRCHO_MDCO` | RACIONAL | (4,3) | Sim | mm, diametro interno do trecho de medicao. |
| `MED_TMPTA_TRCHO_MDCO` | RACIONAL | (3,2) | Sim | Celsius, temperatura de referencia do trecho. |
| `DSC_MATERIAL_CNSTO_TRCHO_MDCO` | TEXTO | 50 | Sim | Material do trecho de medicao. |
| `DSC_LCLZO_TMDA_PRSO_DFRNL` | TEXTO | 50 | Sim | Localizacao das tomadas de pressao diferencial. |
| `IND_TOMADA_PRESSAO_ESTATICA` | TEXTO | 1 | Sim | `M` montante ou `J` jusante. |

### Instrumentos diferenciais de pressao

Aplicavel aos grupos `INST_DIFEREN_PRESSAO_PRINCIPAL`, `INST_DIFEREN_PRESSAO_ALTA`, `INST_DIFEREN_PRESSAO_MEDIA` e `INST_DIFEREN_PRESSAO_BAIXA`.

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE` | TEXTO | 30 | Sim | Numero de serie. |
| `MED_PRSO_LIMITE_SPRR_ALRME` | RACIONAL | (6,3) | Nao | kPa, limite superior. |
| `MED_PRSO_LMTE_INFRR_ALRME` | RACIONAL | (6,3) | Nao | kPa, limite inferior. |
| `IND_HABILITACAO_ALARME` | SIM_NAO | 1 | Nao | `S` ou `N`; observado nos grupos principal/baixa. |
| `MED_PRSO_ADOTADA_FALHA` | RACIONAL | (6,3) | Nao | kPa, valor adotado em falha. |
| `DSC_ESTADO_INSNO_CASO_FALHA` | TEXTO | 50 | Nao | Acao em falha. |
| `MED_CUTOFF_KPA` | RACIONAL | (6,3) | Nao | kPa, cutoff para computo de volume. |

### `PRODUCAO`

| Campo | Natureza | Tamanho | Obrigatorio | Unidade/observacao |
| --- | --- | ---: | --- | --- |
| `DHA_INICIO_PERIODO_MEDICAO` | DATA_HORA | 19 | Sim | Inicio do periodo. |
| `DHA_FIM_PERIODO_MEDICAO` | DATA_HORA | 19 | Sim | Fim do periodo. |
| `ICE_DENSIDADE_RELATIVA` | RACIONAL | (2,8) | Sim | Media ponderada da densidade relativa. |
| `MED_DIFERENCIAL_PRESSAO` | RACIONAL | (6,3) | Sim | kPa, media ponderada do diferencial. |
| `MED_PRESSAO_ESTATICA` | RACIONAL | (6,3) | Sim | kPa. |
| `MED_TEMPERATURA` | RACIONAL | (3,2) | Sim | Celsius. |
| `PRZ_DURACAO_FLUXO_EFETIVO` | RACIONAL | (4,4) | Sim | Minutos. |
| `MED_CORRIGIDO_MVMDO` | RACIONAL | (6,5) | Sim | 10^3 m3, volume corrigido movimentado. |

## Regras de validacao SGMed

- Validar raiz `a003` e codigo de arquivo `003`.
- Correlacionar `COD_TAG_PONTO_MEDICAO` com o cadastro de pontos de medicao.
- Correlacionar `NUM_SERIE_COMPUTADOR_VAZAO` com o CV cadastrado.
- Para pontos de placa/orificio, validar existencia e conteudo de `PLACA_ORIFICIO`.
- Verificar se existe ao menos uma configuracao diferencial aplicavel: principal ou faixas alta/media/baixa.
- Campos criticos: composicao cromatografica, norma de calculo, diametros, materiais, tomadas de pressao, limites de diferencial, cutoff, valores adotados em falha e volume corrigido.
- No caso do tag `45FT0555`, esperado no exemplo: XML 003, CV `20-50-01-048`, sistema `GTG Fuel Gas` no cadastro interno, Run 1.
