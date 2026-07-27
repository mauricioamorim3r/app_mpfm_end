# QA Stabilization Log

## Status

Backend and frontend were modularized and then exercised with API-level validation.
The application is now in a stabilized state for local operation, with remaining risk concentrated in visual/manual browser QA.

## Latest Regression Check

2026-04-27:

- Full automated suite: `python -m pytest -q`
- Result: `288 passed`
- API and UI tests now authenticate against the current HTTP Basic auth configuration.
- Pytest collection now targets `tests/`, avoiding legacy/reference files under `old/`.
- Alarm UI tests now match the current FCS320 PDF upload flow.
- `scripts/api_smoke_test.py` now authenticates against HTTP Basic auth and validates chart, XML042 and export endpoints.

2026-04-27 real-file acceptance:

- Isolated runtime with temporary DB processed the real MPFM Daily PDFs under `data/uploads`.
- Result: 6 MPFM PDFs validated, 0 failed files, latest production date `2026-04-09`.
- Measurement folder discovery now ignores reserved alarm subfolders such as `data/uploads/alarmes`, keeping production PDF/TXT allocation separate from FCS320 alarm imports.
- Real FCS320 alarm PDFs under `data/uploads/alarmes` imported through `/api/alarmes/upload-pdfs`: 3 files, 115 active alarm records.
- Real XML042 samples under `data/outputs/xml042_imported` imported through `/api/xml042/import`: 3 files, 0 errors, exported XLSX valid.
- MPFM summary, chart series, MPFM CSV/XLSX, SEP CSV/XLSX and production XLSX exports returned valid payloads in isolated runtime.
- Production XLSX was confirmed functional; the slow `CARDS_RESUMO` workbook tab was later removed by operational decision.
- No real SEP TXT production file was found in this folder outside docs/legacy/runtime notes; SEP TXT behavior remains covered by parsing tests and synthetic smoke coverage.

2026-04-27 no-cards workbook acceptance:

- Monthly MPFM workbook generation and production Excel export no longer include `CARDS_RESUMO`.
- Backward-compatible calls with `include_cards=1` are ignored for workbook generation and still return valid XLSX.
- Real-file isolated check with 6 MPFM PDFs: production Excel exported in about 35s and no cards sheet was present.
- Existing templates, docs workbooks and `data/outputs/*.xlsx` were sanitized to remove `CARDS_RESUMO`, `Resumo Cards` and `Comparação Base x Resumo`.

2026-04-27 release packaging:

- Documentation updated for stabilized delivery.
- Distribution package generated with `python scripts/make_dist_package.py`.
- Package contents include application code, docs, templates, local DB, sanitized user preferences and principal workbooks.
- Source changes prepared for GitHub push to `origin/main`.

## Fixed During Stabilization

- `GET /api/health` no longer fails with `500` when the local DB is empty or not initialized.
- Manual SEP measurements now appear correctly in `/api/sep/data` when filtered by bank.
- `GET /api/export-sep-csv` no longer fails with `500`.
- SEP exports now treat `unit` consistently as `bank`, matching the UI.
- `GET /api/export-producao-excel` was restored from the legacy implementation and reconnected to the current modular backend.
- The "Excel Produção" frontend flow now defaults missing `include_*` toggles to enabled instead of silently disabling sheets.
- Folder-based production import now skips reserved alarm subfolders so FCS320 PDFs are not reported as invalid production PDFs.
- `CARDS_RESUMO` is no longer generated in monthly workbooks or production Excel exports; stale template tabs are removed during generation and smoke-tested.
- Shared frontend state now initializes:
  - `sepFluidRows`
  - `sepAllDbCols`
  - `deadlines`
- The global month selector now falls back to the current month on a fresh/empty local DB, so date-driven screens still boot with usable defaults.
- After creating or updating PVT parameters, the reconciliação execution tab now refreshes its bank/PVT selectors immediately.
- Mobile/small-viewport topbar layout was adjusted to wrap controls instead of clipping action buttons.

## Validated Flows

- Automated isolated smoke test via `python scripts/api_smoke_test.py`
- Automated isolated UI bootstrap check:
  - `GET /` returned `200`
  - main HTML loaded expected frontend modules
  - all primary `/static/app*.js` and CSS assets returned `200`
- Playwright navigation pass across:
  - resumo
  - upload
  - MPFM
  - separador
  - cards
  - gráficos
  - alertas
  - prazos
  - cadastro
  - reconciliação
  - exportar
- Playwright modal/interactivity pass:
  - settings modal
  - MPFM column picker
  - SEP column picker
  - PVT modal
  - SEP alignment create
  - deadline create
  - focused manual card create flow
- Desktop screenshots captured under `docs/qa_screens/`
- Visual refresh round for remaining pages:
  - upload
  - gráficos
  - cadastro
  - exportar
- Desktop screenshots for the final visual round captured under `docs/qa_screens_round4/`
- Mobile screenshot captured under `docs/qa_screens_mobile/`
- Health and dashboard endpoints
- Monthly summary
- Processing history
- MPFM data listing
- SEP data listing
- SEP fluid detail listing
- Deadlines CRUD
- User preferences read/write
- Cadastro read/write
- PVT params CRUD
- SEP alignment CRUD
- Manual MPFM measurement CRUD
- Manual SEP measurement CRUD
- Manual cards create/list/delete
- MPFM CSV export
- MPFM Excel export
- SEP CSV export
- SEP Excel export
- Cards PDF export
- Production Excel export

## Remaining Manual QA

- Open the UI in a browser and validate each page visually.
- Validate cross-page navigation and refresh behavior.
- Validate upload flow end-to-end with a real SEP TXT file when one is available in this project folder.
- Validate reconciliação end-to-end with a day that has sufficient hourly MPFM + SEP data.

## Notes

- The `appwork/` folder is legacy/reference material and is not part of the active app runtime.
- A previously running local server on port `8765` may still point to an older build; restart local runtime before final user validation.
- `scripts/api_smoke_test.py` can be used for repeatable regression checks after future refactors.
