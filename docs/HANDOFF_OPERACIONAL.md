# Handoff Operacional

## Estado atual

O projeto saiu de uma estrutura monolítica para uma arquitetura modularizada e validada em nível de API.
O backend hoje está distribuído entre `routes/`, `services/` e `repositories/`.
O frontend foi quebrado em módulos JS por domínio dentro de `static/`.

## Ponto de entrada

- Backend: `python server.py`
- Frontend: servido pelo próprio backend em `http://localhost:8765`
- Healthcheck: `GET /api/health`
- Smoke test isolado: `python scripts/api_smoke_test.py`

## Estrutura principal

- `server.py`
  - composição principal do app
- `routes/`
  - endpoints FastAPI por domínio
- `services/`
  - regras de negócio, ingestão e montagem de visões
- `repositories/`
  - acesso SQLite por domínio
- `static/`
  - frontend modularizado
- `docs/`
  - documentação técnica e registro de estabilização

## O que já foi validado

- health
- dashboard
- summary operacional
- CRUD de preferências, cadastro, PVT, deadlines e alinhamentos SEP
- medições manuais MPFM e SEP
- cards manuais
- exports MPFM, SEP, cards PDF e produção Excel
- smoke test automático isolado

## O que ainda depende de validação manual

- navegação visual entre telas
- comportamento de modais
- upload/processamento com arquivos reais
- reconciliação completa com massa horária real suficiente

## Observações importantes

- `appwork/` é legado e não participa da execução normal.
- Há arquivos antigos de backup e artefatos de teste na raiz. Eles foram mantidos como referência local, mas estão ignorados no `.gitignore`.
- Se existir um servidor antigo rodando na porta `8765`, reinicie antes de validar a build atual.

## Próximo passo recomendado

Executar esta sequência:

```bash
python scripts/api_smoke_test.py
python server.py
```

Depois abrir a UI no navegador e percorrer as telas principais com a checklist em `docs/QA_STABILIZATION_LOG.md`.
