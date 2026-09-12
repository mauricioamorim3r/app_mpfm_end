# XML 042 Multifásico — Standalone

Automação externa para gerar arquivos **XML 042** a partir de uma planilha **Base_Unica**, sem depender do app local, `server.py` ou banco SQLite.

Além da Base_Unica informada pelo usuário, a automação possui um **fallback mensal**: se a Base_Unica não puder ser lida ou não gerar candidatos XML042 para a janela solicitada, o script procura automaticamente o arquivo mensal correspondente em `data\outputs`, por exemplo `MPFM_AGO_2026.xlsx` para agosto/2026.

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

1. caminho do Excel Base_Unica **ou da pasta onde ele está**;
2. data inicial da janela;
3. data final da janela.

Se a primeira tentativa na Base_Unica não funcionar, a automação usa a pasta mensal configurada em `config_xml042_standalone.json`:

```json
"monthly_outputs_dir": "..\\..\\data\\outputs"
```

Nesta pasta, o nome esperado é:

```text
MPFM_<MES>_<ANO>.xlsx
```

Exemplos:

```text
MPFM_AGO_2026.xlsx
MPFM_JUL_2026.xlsx
MPFM_SET_2026.xlsx
```

Se o usuário pedir uma janela de outro mês/ano, o script busca o arquivo daquele mês automaticamente. Para uma janela cruzando dois meses, ele tenta ler os dois arquivos mensais necessários.

Se você informar uma pasta, a automação procura automaticamente, nesta ordem:

1. `BASE_UNICA_TOTAL.xlsx`
2. `BASE_UNICA.xlsx`
3. `BASE_UNICA_TOTAL*.xlsx`
4. `BASE_UNICA_STANDALONE*.xlsx`
5. `*BASE_UNICA*.xlsx`

Exemplo de pasta aceita:

```text
C:\Users\MAUAM\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\3.1 Registros Diarios MPFM\Zip\BASE_UNICA_STANDALONE_PACOTE_INCREMENTAL_MANUAL_SAFE_20260804\RevisadoGPT
```

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

Também é permitido informar uma pasta em `--base-unica`:

```powershell
python gerar_xml042_standalone.py --base-unica "D:\Saidas" --date-from 01/08/2026 --date-to 03/08/2026
```

Exemplo escolhendo pasta de saída:

```powershell
python gerar_xml042_standalone.py --base-unica "D:\Saidas\BASE_UNICA_TOTAL.xlsx" --date-from 2026-08-01 --date-to 2026-08-03 --output-dir "D:\XML042_GERADOS"
```

Exemplo forçando a pasta dos arquivos mensais de fallback:

```powershell
python gerar_xml042_standalone.py --base-unica "D:\Saidas\BASE_UNICA_TOTAL.xlsx" --monthly-dir "C:\Users\MAUAM\OneDrive - Equinor\Desktop\app_mpfm_end-main\data\outputs" --date-from 2026-08-01 --date-to 2026-08-03
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
| `PE_4` / `PE-4A` | `7-BAC-5A-SPS` | `86316030256` | `18FT1506` | `B05` |

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

Por padrão, se o mesmo `production_day + cod_cadastro_poco` já constar no manifesto, a automação não gera novamente. Para forçar nova geração, use:

```powershell
python gerar_xml042_standalone.py --base-unica "D:\BASE_UNICA_TOTAL.xlsx" --date-from 2026-08-01 --date-to 2026-08-03 --overwrite
```

### `linhas_rejeitadas_xml042.csv`

Lista linhas ignoradas por motivos como:

- volume crítico ausente;
- sem cadastro XML042;
- cadastro ambíguo.

## Observações importantes

- A automação não altera o Excel Base_Unica.
- A automação não acessa banco de dados.
- A automação não precisa que o app esteja aberto.
- Feche o Excel de saída se for abrir `manifesto_xml042.csv` enquanto roda nova geração.
- O XML gerado segue a estrutura usada pelo app em `services/xml042/xml042_service.py`.
