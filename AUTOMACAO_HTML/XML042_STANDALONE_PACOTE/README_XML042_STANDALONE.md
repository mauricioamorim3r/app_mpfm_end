# XML 042 Multifásico — Standalone

Automação externa para gerar arquivos **XML 042** a partir de uma planilha **Base_Unica**, sem depender do app local, `server.py` ou banco SQLite.

A automação lê a janela de datas informada pelo usuário, filtra as linhas **Daily / MPFM / Subsea** do Excel, identifica os poços cadastrados para XML042 e gera os arquivos no padrão ANP:

```text
042_<CNPJ8>_<AAAAMMDDHHmmSS>.xml
```

Exemplo:

```text
042_04028583_20260806143005.xml
```

## Conteúdo do pacote

- `gerar_xml042_standalone.py` — script principal autocontido.
- `config_xml042_standalone.json` — configuração de CNPJ, catálogo de poços e opções.
- `requirements_xml042_standalone.txt` — dependências mínimas.
- `executar_xml042_standalone.bat` — execução interativa no Windows.
- `README_XML042_STANDALONE.md` — este guia.

## Requisitos

- Windows com Python 3.10 ou superior.
- Excel Base_Unica gerado pela automação Base_Unica ou pelo app.
- Dependências Python:
  - `pandas`
  - `openpyxl`

Para instalar manualmente:

```powershell
python -m pip install -r requirements_xml042_standalone.txt
```

## Execução interativa

Dê duplo clique em:

```text
executar_xml042_standalone.bat
```

O script irá pedir:

1. caminho do Excel Base_Unica ou da pasta que contém `BASE_UNICA_TOTAL.xlsx`;
2. data inicial da janela;
3. data final da janela.

As datas podem ser informadas como:

```text
DD/MM/AAAA
```

ou

```text
AAAA-MM-DD
```

## Execução por linha de comando

Exemplo:

```powershell
python gerar_xml042_standalone.py --base-unica "D:\Saidas\BASE_UNICA_TOTAL.xlsx" --date-from 01/08/2026 --date-to 03/08/2026
```

Exemplo escolhendo pasta de saída:

```powershell
python gerar_xml042_standalone.py --base-unica "D:\Saidas\BASE_UNICA_TOTAL.xlsx" --date-from 2026-08-01 --date-to 2026-08-03 --output-dir "D:\XML042_GERADOS"
```

Exemplo informando aba específica:

```powershell
python gerar_xml042_standalone.py --base-unica "D:\Saidas\BASE_UNICA.xlsx" --sheet "BASE_UNICA_STANDALONE" --date-from 2026-08-01 --date-to 2026-08-03
```

## Abas aceitas automaticamente

Se `--sheet` não for informado, a automação procura nesta ordem:

1. `BASE_UNICA_TOTAL`
2. `BASE_UNICA_MES`
3. `BASE_UNICA_STANDALONE`
4. `Base_Unica`
5. `BASE_UNICA`

## Dados usados no XML

A automação usa as linhas com:

- `Granularity = Daily`
- `Origin = MPFM`
- `Tipo = Subsea`, se habilitado no config
- `IsOfficial = verdadeiro`, se a coluna existir e a opção estiver habilitada

Campos usados para o XML:

| Campo XML | Coluna Base_Unica |
|---|---|
| `COD_CADASTRO_POCO` | catálogo em `config_xml042_standalone.json` |
| `IND_TIPO_TESTE` | fixo `M` para multifásico |
| `DHA_TESTE` | `ProductionDate` às 00:00:00 |
| `DHA_APLICACAO` | `ProductionDate` às 00:00:00 |
| `IND_VALIDO` | fixo `S` |
| `MED_POTENCIAL_OLEO` | `PVT vol Óleo (m³)` |
| `MED_POTENCIAL_GAS` | `PVT vol Gás (Sm³)` dividido por 1000 |
| `MED_POTENCIAL_AGUA` | `PVT vol Água (m³)` |

Os números são gravados com vírgula decimal, como no XML usado pelo app.

## Catálogo de poços

O arquivo `config_xml042_standalone.json` já vem com os poços ativos conhecidos:

| Poço operacional | Poço ANP | Código cadastro | TAG subsea | Banco |
|---|---|---:|---|---|
| `PE_2` | `7-BAC-1-SPS` | `86316029925` | `18FT0506` | `B10` |
| `PW-104DA` | `7-BAC-4D-SPS` | `86316030246` | `18FT1106` | `B15` |
| `PE_4A` (também identificado como `PE_4`, `PE-4` ou `PE-04`) | `7-BAC-5A-SPS` | `86316030256` | `18FT1506` | `B05` |

Se outro poço passar a ser elegível para XML042, adicione-o ao array `catalog` no JSON.

## Saída gerada

Por padrão, os arquivos são salvos dentro da própria pasta da automação:

```text
XML042_STANDALONE_PACOTE/
  xml042_gerados/
    042_04028583_YYYYMMDDHHMMSS.xml
    manifesto_xml042.csv
    linhas_rejeitadas_xml042.csv
```

### `manifesto_xml042.csv`

Registra cada XML gerado, incluindo:

- data de geração;
- data de produção;
- código do poço;
- banco;
- volumes usados;
- nome do XML;
- hash do arquivo.

## Unicidade obrigatória da emissão

Cada combinação `production_day + cod_cadastro_poco` pode ser emitida uma única vez. A trava independe do nome do arquivo e da pasta de saída. Uma nova tentativa:

- não cria outro XML;
- informa o nome e a data da emissão original;
- registra a tentativa bloqueada;
- avisa se o conteúdo solicitado diverge do conteúdo já emitido.

O controle fica em um banco SQLite persistente no perfil local do usuário e é marcado como oculto no Windows. A opção antiga `--overwrite` foi desativada e não contorna a trava.

Para garantir unicidade entre vários computadores, configure `registry_path` no JSON para uma pasta corporativa compartilhada com acesso controlado. Sem essa configuração, a proteção é por usuário/computador.

O arquivo `historico_emissoes_xml042.csv` acompanha o pacote e inicializa o registro com as emissões históricas conhecidas. Para importar outras pastas antigas antes de gerar, use uma ou mais vezes:

```powershell
python gerar_xml042_standalone.py --history-dir "D:\Historico XML042" --base-unica "D:\BASE_UNICA_TOTAL.xlsx" --date-from 2026-08-01 --date-to 2026-08-03
```

Também é possível manter essas pastas no array `history_dirs` do JSON. Se dois XMLs históricos diferentes tiverem o mesmo dia + poço, a aplicação registra `HISTORY_CONFLICT` e bloqueia a geração até a divergência ser investigada.

### `linhas_rejeitadas_xml042.csv`

Lista linhas ignoradas por motivos como:

- volume crítico ausente;
- sem cadastro XML042;
- cadastro ambíguo.
- duplicidade crítica de dia + poço na Base Única.

## Observações importantes

- A automação não altera o Excel Base_Unica.
- A automação mantém somente um registro SQLite local de emissões e tentativas; não acessa banco operacional.
- A automação não precisa que o app esteja aberto.
- Feche o Excel de saída se for abrir `manifesto_xml042.csv` enquanto roda nova geração.
- O XML gerado segue a estrutura usada pelo app em `services/xml042/xml042_service.py`.
