# PRD — Twin MPFM Bacalhau (E1 build memory)

## Problema original (verbatim)
> "criar aplicação conforme documentação" + PRD anexo + `Twin_MPFM_App_Integrada_v4.zip`
> Auditoria (Iteração 3): "verificar se temos uma aplicação confiável, modular e pronta para evolução"

## Estado atual (Iteração 3 — 12/06/2026, pós-auditoria)

### Stack
- **Backend**: FastAPI 0.110 + MongoDB 4.5 (motor) + Pydantic v2 + openpyxl + uvicorn 0.25 com hot reload e `lifespan` async
- **Frontend**: React 19 + craco + fetch nativo (sem axios/react-query); SPA single-page com state switching
- **Banco**: MongoDB local (`test_database`) — collections: `analyses`, `pvt_catalog`, `mpfm_records`
- **Testes**: pytest 9 — **75 passes** (20 integração HTTP + 55 unit puros + 6 validação)

### Arquitetura — backend (`/app/backend/`)
```
backend/
├── server.py                       (286 linhas — apenas schemas + rotas)
├── services/
│   ├── __init__.py
│   ├── calculations.py             (motor metrológico — 11 fórmulas v4 literais)
│   └── importers.py                (parser MPFM xlsx)
└── tests/
    ├── backend_test.py             (20 integration tests via HTTP)
    └── test_calculations_unit.py   (55 unit tests puros)
```

### Arquitetura — frontend (`/app/frontend/src/`)
```
src/
├── App.js                          (127 linhas — apenas orquestração)
├── calculations.js                 (motor de cálculo client-side, espelha backend)
├── index.css                       (estilos v4 verbatim, ~330 linhas)
├── lib/
│   ├── api.js                      (cliente HTTP: api.health/analyze/listPVT/createPVT/importMpfm)
│   └── constants.js                (NAV_ITEMS, DEFAULT_*, lists)
├── components/                     (12 componentes reutilizáveis)
│   ├── Sidebar.jsx, TopBar.jsx
│   ├── FilterBar.jsx, KpiCards.jsx
│   ├── EnvelopeChart.jsx, DecisionPanel.jsx
│   ├── ComparisonCards.jsx, QualityList.jsx, AlertsList.jsx
│   ├── HistoryTable.jsx, HistoryStrip.jsx
│   └── ReportDialog.jsx
└── views/                          (8 views da SPA)
    ├── ConsultorView.jsx, BalanceView.jsx
    ├── PVTView.jsx, EnvelopeView.jsx
    ├── RCAView.jsx, MemorialView.jsx
    ├── ConfigView.jsx, DesignView.jsx
```

### Rotas API v4 (todas em `/api/*`)
- `GET /api/health` — health-check com versão
- `GET /api/constants` — 13 constantes metrológicas
- `POST /api/consultor/analyze` — motor completo (metrics, balance, deviations, mpfmMasses, alerts, lineage); persist=true grava em `analyses`
- `POST /api/separator-balance/calculate` — balanço de massas isolado
- `GET /api/analyses` / `GET /api/analyses/{id}` / `GET /api/analyses/{id}/memorial` (text/plain Markdown)
- `GET /api/pvt/catalog` / `POST /api/pvt/catalog`
- `POST /api/import/mpfm-xlsx` (validação extensão + try/except corrupt + records_rejected) / `GET /api/import/mpfm-records`

### Fórmulas metrológicas (preservadas literais do v4)
```
NSV_sep            = GSV_sep × (1 - BSW/100)
V_STO              = NSV_sep × SF_sep_tank
m_oil_REF          = V_STO × ρ_oil_STO / 1000
V_gas_flash_std    = V_STO × ΔRs_sep_tank
V_gas_total_std    = V_gas_sep_std + V_gas_flash_std
m_gas_REF          = V_gas_total_std × ρ_gas_std / 1000
V_water_total_std  = V_water_free_std + GSV_sep × BSW/100
m_water_REF        = V_water_total_std × ρ_water_20 / 1000
m_HC_REF           = m_oil_REF + m_gas_REF
m_total_REF        = m_HC_REF + m_water_REF
En                 = (x_MPFM - x_REF) / √(U_MPFM² + U_REF²)
GVF                = qg_actual / (qg_actual + qo + qw)
WLR                = qw / (qo + qw)
GOR                = qg / qo
δ_phase (%)        = 100 × (x_MPFM - x_REF) / x_REF
IAJ                = clamp(100 - penalidades, 0, 100)
Fator sugerido     = m_HC_REF / m_HC_MPFM
```

### Rastreabilidade (regras do projeto preservadas)
- ✅ FCS320 / PVTPack tratados como `external_reference` / `black-box`
- ✅ EOS = `independent_validation` (não declara equivalência plena com PVTPack nativo)
- ✅ Rota = `inferred` (não `confirmed` por válvulas)
- ✅ Gas lift = `provided` se >0 senão `not_confirmed` + alerta no memorial
- ✅ PVT nativo = `native_pvt_available: false`
- ✅ Memorial registra explicitamente cada limitação na seção "Observações técnicas"

### Auditoria — correções aplicadas na Iteração 3
| # | Correção | Resultado |
|---|---|---|
| 1 | Limpar collections órfãs da iter-1 (windows/pvt_samples/applicability_runs/kfactor_runs) | 4 collections dropped; só sobraram as 3 do v4 |
| 2 | Modularizar `server.py` (534→286 linhas) em `services/calculations.py` + `services/importers.py` | Lint clean, 14/14 integração mantidos |
| 3 | 55 unit tests puros (`test_calculations_unit.py`) — cobre cada fórmula | 55/55 pass em 0.07s |
| 4 | Validação Pydantic (`Field(ge=0/le=100/gt=0)`) + importador robusto (try/except → 400) | +6 tests; nenhum 500 em xlsx corrompido |
| 5 | `@app.on_event("shutdown")` → `lifespan` async context manager | Sem deprecation warning |
| 6 | Componentizar `App.js` (975→127 linhas) em 12 components + 8 views + 2 libs | Lint clean; 39/39 frontend selectors mantidos |

### Code Review — Iteração 4 (aplicação seletiva)

**Aplicado:**
| Item | Resultado |
|---|---|
| Defensive `records = []` init em `server.py` antes do try | linter satisfeito; comportamento idêntico |
| Split `import_mpfm_xlsx` em 5 helpers (`_find_header_row`, `_normalize_headers`, `_row_is_empty`, `_cell_to_serializable`, `_parse_row`) | CC 19→4; comportamento idêntico |
| Extração `_compute_kinematic_metrics` em `analyze()` | CC 13→7; fórmulas intocadas |
| Content-based keys em 7 listas (EnvelopeChart, QualityList, HistoryTable, HistoryStrip, AlertsList, RCAView, KpiCards) | ZERO React "unique key" warnings |
| `KpiCard` sub-component + `pillClass` helper extraídos de `KpiCards` | CC 11→2 |
| `PVTModal` + `PVTCatalogTable` extraídos de `PVTView` (119→75 linhas) | Componentes reutilizáveis |
| 3 custom hooks: `useTheme`, `useApiConnection`, `usePvtCatalog` | App.js de 127→89 linhas |
| `AppRouter.jsx` substitui 8 conditionals do switching de view | CC do App: 17→4 |
| `data-testid="sidebar"` adicionado pelo testing agent | Melhoria de testabilidade |

**Recusado (com justificativa documentada):**
| Recomendação recusada | Justificativa |
|---|---|
| Split `separator_balance()` em gas/oil/water sub-funções | **Regra #2 do projeto**: fórmulas devem ler sequencialmente como na documentação metrológica; indireção esconde a auditoria |
| Split `build_memorial()` em header/body/footer | **Regra #3 do projeto**: "Preserve a lógica do memorial"; é um único template auditável |
| `is not None` → `== None`, `is False` → `== False` | **Falsos positivos**: PEP 8 EXIGE `is`/`is not` para `None`; `is False` é idioma recomendado para asserts de boolean estrito |
| Hook deps `localStorage`, setters, promise vars (App.js) | `localStorage` é global; setters do React são estáveis; `d` é variável local da promise |
| Modificar `use-toast.js` | Arquivo do shadcn stock, fora do escopo |

### Métricas finais (pós-iteração 4)
- ✅ Backend: **75/75 pytest** pass (~1.9s contra URL pública)
- ✅ Frontend: 100% — todos os fluxos críticos verificados pelo testing agent (iteration_4.json)
- ✅ Lint Python: clean
- ✅ Lint JS/JSX: clean
- ✅ Zero React warnings no console
- ✅ Fórmulas e memorial preservados (NSV_sep com defaults = 194.724096 — bit-exact iguais à iteração 3)
- ✅ Visual fiel ao mockup v4 mantido

### Estado atual da árvore
```
backend/
├── server.py                       (298 linhas — schemas + rotas)
├── services/
│   ├── calculations.py             (motor — 11 fórmulas v4 literais + _compute_kinematic_metrics)
│   └── importers.py                (parser MPFM xlsx + 5 helpers privados, CC=4)
└── tests/
    ├── backend_test.py             (20 integration tests + validação Pydantic)
    └── test_calculations_unit.py   (55 unit tests puros)

frontend/src/
├── App.js                          (89 linhas — orquestração mínima)
├── AppRouter.jsx                   (37 linhas — mapa view→componente)
├── calculations.js                 (cálculos client-side)
├── lib/{api.js, constants.js}
├── components/                     (14 .jsx)
│   ├── Sidebar, TopBar, FilterBar
│   ├── KpiCards (com sub-KpiCard), EnvelopeChart
│   ├── DecisionPanel, ComparisonCards, QualityList, AlertsList
│   ├── HistoryTable, HistoryStrip, ReportDialog
│   └── PVTModal, PVTCatalogTable
├── views/                          (8 .jsx)
└── hooks/                          (3 custom hooks: useTheme, useApiConnection, usePvtCatalog)
```

## Backlog futuro
### P1 (pronto para evoluir, sem quebrar MVP)
- Migração SQLite → PostgreSQL: introduzir camada `services/repository.py` abstraindo Mongo; trocar adaptador
- Migração SPA → Next.js: componentes/views já modulares; mover para `pages/*` é mecânico
- Vincular PVT ativo no Consultor (seletor que puxa de `/api/pvt/catalog`)
- Workflow de aprovação metrológica do fator sugerido (assinatura digital)
- Importar planilhas reais MPFM_MAR_2026.xlsx / MAI_2026.xlsx

### P2
- Conector NeqSim para SRK/Peneloux em runtime
- Autenticação corporativa + RBAC
- Pipeline bronze/silver/gold com tendências por poço
- Pacote de auditoria assinado (.zip Markdown + PDF + Excel + JSON)

### P3
- Conector PI/FCS320 automático
- Confirmação de rota por válvulas via SCADA
- Deploy cloud
