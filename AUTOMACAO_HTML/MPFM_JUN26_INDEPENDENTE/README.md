# MPFM Junho/2026 — automação independente

Esta pasta é independente da automação `Base Única Total`.

Origem padrão: `C:\MPFM\NOVO\data\outputs\MPFM_JUN_2026.xlsx`

Gerar novamente:

```powershell
C:\Python313\python.exe .\gerar_mpfm_jun26.py
```

Saída: `MPFM_JUN26_INDEPENDENTE.html`.

O fluxo lê as abas originais `BASE_UNICA_MES`, `DAILYS`, `HOURLYS`, `RECON`, `ALERTAS_MES` e `STATUS_MES`, sem modificar colunas ou formatação do Excel e sem importar a lógica da Base Única Total. PI é explicitamente marcado como indisponível nesta base.

O comparativo entre as duas entradas SEP está em `COMPARATIVO_SEP_JUNHO_2026.md`, com os valores por dia em `comparativo_sep_junho_2026.csv`. Para regenerar: `C:\Python313\python.exe .\comparar_sep_entradas.py`.
