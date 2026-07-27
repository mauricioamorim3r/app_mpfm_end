# XML 004 - registros de alarmes e eventos

Fonte base: `referencias_doc/Manual XML 004.pdf` e exemplo `referencias_doc/004_04028583_20260415001000_38480.xml`.

## Finalidade

O XML 004 descreve alarmes e eventos ocorridos em um determinado periodo de producao por computador de vazao. Na aplicacao SGMed, este XML e a base principal para monitoramento de alarmes e para a area de gestao de alarmes.

## Nomenclatura do arquivo

Formato obrigatorio:

```text
004_bbbbbbbb_cccccccccccccc.ddd
```

| Parte | Regra |
| --- | --- |
| `004` | Codigo fixo do arquivo. Nao deve ser alterado. |
| `bbbbbbbb` | 8 primeiros digitos do CNPJ da operadora. |
| `cccccccccccccc` | Data/hora de geracao no formato `AAAAMMDDHHmmSS`. |
| `ddd` | `xml` para arquivo descompactado ou `zip` para compactado. |

Exemplo: `004_04028583_20260415001000_38480.xml`.

Observacao operacional: para analise cronologica e de periodo, usar os campos internos `DHA_ALARME` e `DHA_OCORRENCIA_EVENTO`, nao a data do nome do arquivo.

## Regras gerais de formato

| Item | Regra |
| --- | --- |
| Raiz | Elemento raiz deve ser `<a004>`. |
| Estrutura | Manter estrutura inalterada mesmo quando nao houver alarmes ou eventos. |
| Campos vazios | Usar elemento vazio quando aplicavel. |
| Numeros racionais | Usar virgula decimal nos campos numericos definidos como racional. No exemplo, `DSC_MEDIDA_ALARMADA` pode vir como texto numerico com ponto, pois sua natureza e `TEXTO`. |
| Datas | `DATA_HORA` no formato `DD/MM/AAAA HH:mm:SS`, com 19 caracteres. |
| Texto | Respeitar tamanho maximo do manual para cada campo. |
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
<a004>
  <LISTA_DADOS_BASICOS>
    <DADOS_BASICOS NUM_SERIE_COMPUTADOR_VAZAO="..." COD_INSTALACAO="...">
      <LISTA_ALARMES>
        <ALARMES>
          <DSC_DADO_ALARMADO>...</DSC_DADO_ALARMADO>
          <DHA_ALARME>...</DHA_ALARME>
          <DSC_MEDIDA_ALARMADA>...</DSC_MEDIDA_ALARMADA>
        </ALARMES>
      </LISTA_ALARMES>
      <LISTA_EVENTOS>
        <EVENTOS>
          <DSC_DADO_ALTERADO>...</DSC_DADO_ALTERADO>
          <DSC_CONTEUDO_ORIGINAL>...</DSC_CONTEUDO_ORIGINAL>
          <DSC_CONTEUDO_ATUAL>...</DSC_CONTEUDO_ATUAL>
          <DHA_OCORRENCIA_EVENTO>...</DHA_OCORRENCIA_EVENTO>
        </EVENTOS>
      </LISTA_EVENTOS>
    </DADOS_BASICOS>
  </LISTA_DADOS_BASICOS>
</a004>
```

## Cardinalidade dos grupos

| Grupo | Minimo | Maximo | Obrigatorio | Observacao |
| --- | ---: | ---: | --- | --- |
| `DADOS_BASICOS` | 0 | Ilimitado | Sim | Um registro por computador de vazao/instalacao com alarmes ou eventos. |
| `ALARMES` | 0 | Ilimitado | Sim | Alarmes disparados no periodo. |
| `EVENTOS` | 0 | Ilimitado | Sim | Eventos com modificacao de dados no periodo. |

Nota: o manual indica que os grupos `ALARMES` e `EVENTOS` sao conjuntos obrigatorios de estrutura, mas a quantidade de registros esperada pode ser zero.

## Campos obrigatorios por grupo

### `DADOS_BASICOS` atributos

| Campo | Natureza | Tamanho | Obrigatorio | Regra |
| --- | --- | ---: | --- | --- |
| `NUM_SERIE_COMPUTADOR_VAZAO` | TEXTO | 30 | Sim | Numero de serie do computador de vazao. |
| `COD_INSTALACAO` | NATURAL | 10 | Sim | Codigo da instalacao onde o ponto de medicao se encontra. |

### `ALARMES`

| Campo | Natureza | Tamanho | Obrigatorio | Regra |
| --- | --- | ---: | --- | --- |
| `DSC_DADO_ALARMADO` | TEXTO | 50 | Sim | Descricao do dado que causou o disparo do alarme. |
| `DHA_ALARME` | DATA_HORA | 19 | Sim | Data/hora de ocorrencia do alarme. |
| `DSC_MEDIDA_ALARMADA` | TEXTO | 50 | Sim | Conteudo/medida que disparou o alarme. |

Exemplo observado:

```xml
<ALARMES>
  <DSC_DADO_ALARMADO>Run 1 Flow rate alarm from Normal to High  - Alarm</DSC_DADO_ALARMADO>
  <DHA_ALARME>14/04/2026 00:10:41</DHA_ALARME>
  <DSC_MEDIDA_ALARMADA>170.17</DSC_MEDIDA_ALARMADA>
</ALARMES>
```

### `EVENTOS`

| Campo | Natureza | Tamanho | Obrigatorio | Regra |
| --- | --- | ---: | --- | --- |
| `DSC_DADO_ALTERADO` | TEXTO | 50 | Sim | Dado alterado no evento. |
| `DSC_CONTEUDO_ORIGINAL` | TEXTO | 50 | Sim | Conteudo original antes da alteracao. |
| `DSC_CONTEUDO_ATUAL` | TEXTO | 50 | Sim | Conteudo atual depois da alteracao. |
| `DHA_OCORRENCIA_EVENTO` | DATA_HORA | 19 | Sim | Data/hora de ocorrencia do evento. |

## Regras de interpretacao de alarmes

O campo `DSC_DADO_ALARMADO` deve ser preservado integralmente como evidencia. Para analise operacional, a aplicacao pode derivar:

| Informacao derivada | Como extrair |
| --- | --- |
| Run | Procurar padrao `Run N` no texto do alarme. |
| Variavel alarmada | Texto entre `Run N` e `alarm` quando existir, exemplo `Flow rate`. |
| Transicao de estado | Texto apos `from`, exemplo `Normal to High`, `High High to Norma`. |
| Estado final | Sufixo `- Alarm`, `- OK` ou similar. |
| Medida | Valor textual em `DSC_MEDIDA_ALARMADA`; preservar como texto original. |

## Regras de interpretacao de eventos

Eventos devem ser tratados como rastreabilidade de mudanca. A aplicacao deve preservar:

- Dado alterado (`DSC_DADO_ALTERADO`).
- Valor original (`DSC_CONTEUDO_ORIGINAL`).
- Valor atual (`DSC_CONTEUDO_ATUAL`).
- Data/hora da ocorrencia (`DHA_OCORRENCIA_EVENTO`).
- Computador de vazao (`NUM_SERIE_COMPUTADOR_VAZAO`).
- Instalacao (`COD_INSTALACAO`).

Quando um evento representar alteracao metrologica ou de limite de alarme, deve ser marcado para analise e rastreabilidade, mesmo que o XML nao informe usuario/executante.

## Regras de validacao SGMed

- Validar raiz `a004` e codigo de arquivo `004`.
- Correlacionar `NUM_SERIE_COMPUTADOR_VAZAO` com os CVs cadastrados.
- Usar `Run N` no texto para correlacionar com o ponto de medicao do CV, quando possivel.
- Preservar `DSC_DADO_ALARMADO` e `DSC_MEDIDA_ALARMADA` como evidencia textual original.
- Usar `DHA_ALARME` e `DHA_OCORRENCIA_EVENTO` como datas oficiais do evento/alarme.
- Separar a visualizacao tecnica do XML 004 da gestao operacional: XML 004 mostra evidencia importada; Gestao de alarmes registra prioridade, responsavel, status e acao/correcao.
- Campos criticos: alarmes com estado final `Alarm`, alarmes recorrentes, eventos de alteracao de limites, eventos de alteracao de parametros metrologicos e eventos sem valor original/atual claro.
