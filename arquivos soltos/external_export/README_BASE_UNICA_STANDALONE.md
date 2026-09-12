# Base_Unica Standalone

Pacote externo para gerar a planilha `Base_Unica` a partir de relatórios MPFM em PDF e relatórios TXT do Separador de Testes (SEP), sem depender do servidor local, banco SQLite ou restante do projeto `app_mpfm_end`.

A cada execução, o pacote gera um Excel individual da análise e, por padrão, também atualiza uma base consolidada incremental chamada `BASE_UNICA_TOTAL.xlsx`.

## Conteúdo do pacote

- `gerar_base_unica_standalone.py` — script principal autocontido.
- `requirements_base_unica_standalone.txt` — dependências Python mínimas.
- `executar_base_unica_standalone.bat` — atalho Windows para execução interativa.
- `README_BASE_UNICA_STANDALONE.md` — este guia.

## Requisitos

- Windows com Python 3.10 ou superior instalado.
- Acesso às pastas de origem dos relatórios:
  - PDFs MPFM, organizados por banco `B03`, `B08`, `B13`, `B05`, `B10`, `B15`.
  - Daily Reports SEP com pastas `FC13`, `FC14` e `FC17` contendo `Run_24Hours*.txt`.

## Instalação das dependências

Abra o Prompt de Comando ou PowerShell na pasta deste pacote e execute:

```powershell
python -m pip install -r requirements_base_unica_standalone.txt
```

Se houver mais de uma versão de Python instalada, use o caminho completo do Python desejado, por exemplo:

```powershell
"C:\Program Files\Python312\python.exe" -m pip install -r requirements_base_unica_standalone.txt
```

## Execução interativa

A forma mais simples é dar duplo clique em:

`executar_base_unica_standalone.bat`

O script irá pedir:

1. caminho da pasta raiz dos PDFs MPFM;
2. caminho da pasta raiz dos Daily Reports SEP;
3. demais parâmetros ficam nos padrões do script, salvo se você editar ou executar por linha de comando.

## Execução por linha de comando

Exemplo exportando os 5 dias mais recentes disponíveis:

```powershell
python gerar_base_unica_standalone.py --mpfm-root "D:\Relatorios\MPFM" --sep-root "D:\Relatorios\SEP" --output "D:\Saidas\BASE_UNICA.xlsx" --days 5 --aligned-bank B10 --workers 4
```

Exemplo exportando intervalo histórico específico:

```powershell
python gerar_base_unica_standalone.py --mpfm-root "D:\Relatorios\MPFM" --sep-root "D:\Relatorios\SEP" --output "D:\Saidas\BASE_UNICA_20260201_20260802.xlsx" --date-from 01/02/2026 --date-to 02/08/2026 --aligned-bank B10 --workers 4
```

Exemplo escolhendo onde ficará a base total incremental:

```powershell
python gerar_base_unica_standalone.py --mpfm-root "D:\Relatorios\MPFM" --sep-root "D:\Relatorios\SEP" --output "D:\Saidas\BASE_UNICA_DIA.xlsx" --master-output "D:\Saidas\BASE_UNICA_TOTAL.xlsx"
```

Exemplo gerando somente o arquivo individual, sem atualizar a base total:

```powershell
python gerar_base_unica_standalone.py --mpfm-root "D:\Relatorios\MPFM" --sep-root "D:\Relatorios\SEP" --output "D:\Saidas\BASE_UNICA_DIA.xlsx" --no-master
```

## Parâmetros disponíveis

| Parâmetro | Descrição |
|---|---|
| `--mpfm-root` | Pasta raiz onde ficam os PDFs MPFM. |
| `--sep-root` | Pasta raiz onde ficam os Daily Reports SEP. |
| `--output` | Caminho completo do arquivo `.xlsx` de saída. |
| `--master-output` | Caminho completo da `BASE_UNICA_TOTAL.xlsx` incremental. Se omitido, salva ao lado do script. |
| `--no-master` | Não atualiza a base total incremental nesta execução. |
| `--days` | Quantidade de dias mais recentes a exportar quando não há intervalo explícito. |
| `--date-from` | Data inicial do intervalo, em `DD/MM/AAAA` ou `AAAA-MM-DD`. |
| `--date-to` | Data final do intervalo, em `DD/MM/AAAA` ou `AAAA-MM-DD`. |
| `--aligned-bank` | Banco MPFM que receberá o merge das colunas SEP. Padrão: `B10`. |
| `--months-lookback` | Quantidade máxima de meses pesquisados para localizar dados recentes. |
| `--workers` | Número de processos paralelos para leitura dos PDFs. Use `4` como padrão seguro. |

## Estrutura de pastas esperada

### MPFM

O script espera uma pasta raiz contendo subpastas dos bancos configurados internamente:

```text
MPFM_ROOT/
  3.1.1_13-FT-0367 Riser P5 - Topside B03/
    2026/
      07. Julho/
        Daily/
        Hourly/
  3.1.2_13-FT-0167 Riser P2 - Topside B08/
  3.1.3_13-FT-0317 Riser P4 - Topside B13/
  3.1.4_18-FT-1506 PE 4 e PE_EO105 - Subsea B05/
  3.1.5_18-FT-0506 PE 2 - Subsea B10/
  3.1.6_18-FT-1106 PW_104DA - Subsea B15/
```

### SEP

```text
SEP_ROOT/
  2026/
    07. Julho/
      FPSO-Bacalhau_Daily reports_2026-07-29/
        01 - CV_Reports/
          FC13/
            Run_24Hours*.txt
          FC14/
            Run_24Hours*.txt
          FC17/
            Run_24Hours*.txt
```

## Saída gerada

O arquivo Excel contém:

- aba `BASE_UNICA_STANDALONE` com os dados consolidados;
- aba `COMPARATIVO_MANUAL` fixa, para preenchimento manual pelo usuário.

## Base_Unica total incremental

Além do arquivo individual da execução, a automação atualiza por padrão um segundo arquivo:

`BASE_UNICA_TOTAL.xlsx`

Esse arquivo funciona como histórico acumulado de todas as análises geradas. A regra é:

1. lê a base total existente, se houver;
2. junta com as linhas da análise atual;
3. remove duplicidades por chave técnica;
4. mantém a versão mais recente quando o mesmo dia/banco/hora/tag for reprocessado;
5. salva somente a aba `BASE_UNICA_TOTAL` atualizada.

A aba `COMPARATIVO_MANUAL` da `BASE_UNICA_TOTAL.xlsx` é considerada área do usuário. Ela é criada se ainda não existir, mas depois fica isenta da atualização incremental: os dados digitados manualmente pelo usuário não são apagados nem sobrescritos pela automação.

A chave técnica usada para evitar duplicidade é:

```text
ProductionDate + Hour + Granularity + Origin + SourceType + Bank + Entity + Tag + Instrumento
```

Isso permite reprocessar um período sem multiplicar linhas antigas. Se um PDF corrigido for lido novamente, a linha antiga é substituída pela nova no consolidado.

Importante: feche o arquivo `BASE_UNICA_TOTAL.xlsx` no Excel antes de executar a automação; se ele estiver aberto, o Windows pode bloquear a gravação.

## Observações importantes

- O script não acessa banco de dados.
- O script não depende do `server.py`.
- O script não altera os arquivos de origem.
- O arquivo individual de cada análise continua sendo gerado normalmente; a `BASE_UNICA_TOTAL.xlsx` é apenas o consolidado incremental.
- Se a estrutura de pastas da instalação for diferente, ajuste as constantes `BANK_FOLDERS` ou as funções de caminho dentro de `gerar_base_unica_standalone.py`.
- Para exportações históricas grandes, use `--workers 4` ou mais conforme a máquina permitir.

## Solução de problemas

### `ModuleNotFoundError`

Instale as dependências:

```powershell
python -m pip install -r requirements_base_unica_standalone.txt
```

### Nenhum Daily PDF encontrado

Confira se `--mpfm-root` aponta para a pasta acima das subpastas `3.1.x_...` dos bancos.

### SEP incompleto ou não mesclado

Confira se `--sep-root` aponta para a pasta acima do ano/mês dos Daily Reports e se existem arquivos `Run_24Hours*.txt` em `FC13`, `FC14` e `FC17`.

### Execução lenta

A leitura de PDFs é a parte mais pesada. Aumente `--workers` gradualmente, por exemplo `--workers 6` ou `--workers 8`, se o computador tiver CPU/memória disponíveis.
