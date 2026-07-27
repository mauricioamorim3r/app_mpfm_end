# Release Notes - 2026-04-27

## Status

Entrega estabilizada para operação local e publicação no GitHub.

## Principais mudanças

- Mantidas as regras de alocação de data de produção para PDF e TXT.
- PDF de medição usa período extraído do conteúdo do relatório.
- TXT SEP usa período/data do conteúdo antes de qualquer fallback por nome.
- Carga de produção PDF/TXT ignora subpastas reservadas de alarmes FCS320.
- Aba `CARDS_RESUMO` removida dos workbooks mensais e do Excel de produção.
- Templates, workbooks de `data/outputs` e planilhas auxiliares em `docs` saneados para remover abas de cards existentes.
- Gráficos, XML042, alarmes, exportações Excel/CSV e smoke API validados.
- Documentação operacional atualizada.

## Validação

- `python -m pytest -q` -> `289 passed`
- `python scripts/api_smoke_test.py` -> `SMOKE TEST PASSED`
- Aceitação real isolada com 6 PDFs MPFM, 3 PDFs de alarmes FCS320 e 3 XML042.
- Checagem real isolada confirmou Excel mensal e Excel de produção sem abas de cards.

## ZIP

O pacote de distribuição é gerado com:

```powershell
python scripts\make_dist_package.py
```

O script cria `MPFM_DIST_<data_hora>.zip` na pasta pai da aplicação.

## Observações

- O ZIP inclui código, documentação, templates, banco local, preferências sanitizadas e workbooks principais.
- O ZIP não inclui uploads temporários, `.git`, `old/`, `.vscode/` ou caches.
- Um TXT SEP real recente ainda deve ser validado em rodada específica quando for incorporado ao fluxo operacional.
