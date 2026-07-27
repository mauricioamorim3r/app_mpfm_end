# MPFM Manager - pacote de testes/producao

Gerado em: 2026-07-06T07:30:08

## Como iniciar

1. Instale Python 3.11+.
2. Instale dependencias: `pip install -r requirements.txt`.
3. Rode `python server.py` ou use `start_app.ps1`.
4. Acesse `http://localhost:8765`.

## Incluido

- arquivos raiz: 21 arquivo(s)
- repositories: 15 arquivo(s)
- routes: 16 arquivo(s)
- scripts: 50 arquivo(s)
- services: 40 arquivo(s)
- static: 97 arquivo(s)
- templates: 10 arquivo(s)
- docs: 77 arquivo(s)
- design-system: 1 arquivo(s)
- data minima: 31 arquivo(s)
- Painel_Operador/dashboard-anp-radar: 46 arquivo(s)
- twin runtime: 8 arquivo(s)

## Excluido de proposito

- Ambientes virtuais, caches Python, logs temporarios e screenshots.
- `data/backups`, bancos duplicados `*-lt-*`, `data/outputs` e pacotes antigos.
- Builds portateis anteriores em `dist`.
- Massa bruta pesada do Painel Operador, mantendo apenas o modulo `dashboard-anp-radar` sem `node_modules`, `MODELOS`, builds e zips.
- Prototipos internos pesados do Twin, mantendo apenas `twin/index.html` e `twin/assets/a02` usados pela aplicacao.
- `.env` e demais arquivos locais/sensiveis.