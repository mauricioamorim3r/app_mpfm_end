# Plano de contingencia se o Vite nao estiver disponivel

## Status

A contingencia recomendada foi aplicada: a API local saiu do Vite e agora roda em `server/radar-api.mjs`; o frontend e gerado por `scripts/build_frontend.mjs` com `esbuild`; o comando operacional passa a ser `npm run app`.

## Resumo executivo

O impacto era alto, mas controlavel. Nesta aplicacao o Vite tinha dois papeis:

1. Empacotar e servir o frontend React.
2. Hospedar a API local do Radar por meio do plugin `radar-anp-data-api` em `vite.config.js`.

Portanto, perder o Vite nao quebrava apenas `npm run dev` ou `npm run build`; tambem removeria os endpoints locais que salvam configuracoes, reprocessam dados e registram decisoes auditaveis. A migracao separou esses endpoints em um servidor proprio.

## Dependencias removidas do Vite

Arquivos diretamente impactados:

- `package.json`: scripts `app`, `dev`, `preview` e `build` nao chamam mais Vite.
- `server/radar-api.mjs`: contem a API local e serve `dist/`.
- `scripts/build_frontend.mjs`: gera o frontend React com `esbuild`.
- `start-radar-anp.bat`: chama `npm run app`.
- `INSTRUCOES_TESTE.md`: orienta o usuario a rodar `npm run app` e abrir `http://127.0.0.1:6287`.
- `src/App.jsx`: consome os mesmos endpoints `/api/*` e orienta a rodar com `npm run app`.

Endpoints locais agora fornecidos por `server/radar-api.mjs`:

- `GET /api/config`
- `POST /api/config`
- `GET /api/data`
- `POST /api/proposals/decision`
- `POST /api/pendencies/decision`
- `GET /api/database-summary`
- `GET /api/ai-config`
- `POST /api/ai-config`
- `POST /api/rebuild`

## Impacto por funcionalidade

| Area | Impacto original sem Vite | Situacao apos adequacao |
| --- | --- | --- |
| Tela React | Alto | Gerada por `scripts/build_frontend.mjs` com `esbuild`. |
| Build de producao | Alto | `npm run build` chama Python + `esbuild`. |
| Servidor local | Alto | `server/radar-api.mjs` serve `dist/` em `127.0.0.1:6287`. |
| Reprocessar dashboard pela UI | Critico | `POST /api/rebuild` foi migrado para o servidor proprio. |
| Salvar caminhos na UI | Critico | `POST /api/config` foi migrado para o servidor proprio. |
| Decisoes auditaveis | Critico | Endpoints de propostas e pendencias foram migrados. |
| Abrir painel estatico | Medio | `dist/` continua recriavel e pode ser servido pelo servidor proprio. |
| Pipeline Python | Baixo | Continua funcionando independentemente do bundler. |
| SQLite gerado | Baixo | Continua sendo gerado pelo Python. |

## Medidas aplicadas

### 1. Novo comando operacional

Uso recomendado:

```powershell
npm install
npm run app
```

Para gerar apenas os artefatos:

```powershell
npm run build
```

### 2. API local separada do Vite

A logica de API foi movida para um servidor Node proprio:

```text
server/
  radar-api.mjs
```

Esse servidor assume os endpoints `/api/*` e chama `scripts/build_dashboard_data.py` quando o usuario clica em reprocessar.

Resultado esperado:

```powershell
npm run app
```

Abrindo:

```text
http://127.0.0.1:6287
```

Se necessario, outra porta pode ser usada com `RADAR_PORT`.

### 3. Bundler do frontend trocado

O build do frontend foi migrado para `esbuild`, declarado como dependencia direta de desenvolvimento.

Estrutura sugerida:

```text
scripts/
  build_frontend.mjs
```

Saidas esperadas:

```text
dist/
  index.html
  assets/index.js
  assets/index.css
```

Scripts sugeridos:

```json
{
  "scripts": {
    "data": "python scripts/build_dashboard_data.py",
    "test": "python -m unittest discover -s tests -v",
    "build:frontend": "node scripts/build_frontend.mjs",
    "build": "npm run data && npm run build:frontend",
    "app": "node server/radar-api.mjs"
  }
}
```

### 4. Mensagens da UI atualizadas

A UI agora orienta:

```text
Rode o app com npm run app.
```

## Rotas possiveis

### Rota A: Manter Vite congelado temporariamente

Indicada para continuidade imediata.

Vantagens:

- Menor esforco agora.
- Nenhuma mudanca funcional.
- Mantem o fluxo atual.

Riscos:

- Continua dependente de uma ferramenta indisponivel no medio prazo.
- API local segue misturada ao build tool.

### Rota B: Node server proprio + esbuild

Indicada como melhor equilibrio.

Vantagens:

- Mantem React.
- Remove dependencia operacional do Vite.
- Aproveita grande parte da logica atual.
- Permite um unico comando local para UI + API.

Riscos:

- Exige migrar `vite.config.js` para servidor proprio.
- Precisa ajustar build de CSS/assets.

### Rota C: Python server + frontend estatico

Indicada se a prioridade for reduzir dependencias Node no backend local.

Vantagens:

- O pipeline ja e Python.
- Facilita integrar leitura de arquivos, SQLite e processamento.

Riscos:

- Ainda precisa de algum bundler para React, ou reescrever frontend.
- Pode exigir Flask/FastAPI ou servidor HTTP manual.

### Rota D: Aplicacao desktop empacotada

Indicada para ambiente operacional controlado.

Opcoes:

- Electron com Node API local.
- Tauri com backend Rust/sidecar Python.
- Pacote Windows com servidor local + atalho.

Vantagens:

- Melhor experiencia para operador.
- Menos dependencia de comandos manuais.

Riscos:

- Maior esforco de empacotamento e manutencao.

## Recomendacao

Recomendo seguir em duas fases:

### Fase 1 - Contencao

- Manter Vite congelado com lockfile e pacote offline.
- Garantir que `dist/` e `data/radar-anp.sqlite` estejam sempre geraveis.
- Documentar que o modo estatico serve apenas para consulta, nao para reprocessar/salvar.

### Fase 2 - Migracao segura

- Criar servidor local Node proprio para os endpoints `/api/*`.
- Mover a logica de API de `vite.config.js` para `server/radar-api.mjs`.
- Substituir `vite build` por `esbuild` direto.
- Atualizar `start-radar-anp.bat` para chamar `npm run app`.
- Atualizar docs e mensagens da interface.
- Adicionar testes para os endpoints principais antes da troca completa.

## Ordem tecnica sugerida

1. Copiar funcoes utilitarias da API de `vite.config.js` para `server/radar-api.mjs`.
2. Fazer `GET /api/data` funcionar no servidor novo.
3. Fazer servidor servir `dist/`.
4. Migrar `POST /api/rebuild`.
5. Migrar `POST /api/config` e `POST /api/ai-config`.
6. Migrar decisoes de propostas e pendencias.
7. Criar `scripts/build_frontend.mjs` com `esbuild`.
8. Trocar scripts em `package.json`.
9. Atualizar `start-radar-anp.bat` e docs.
10. Rodar `npm test`, `npm run data`, `npm run build` e teste manual no navegador.

## Conclusao

A indisponibilidade do Vite nao impede o Radar ANP de continuar existindo, porque a regra de negocio principal esta no Python e os dados consolidados ficam em JSON/SQLite. O ponto sensivel e que o Vite hoje virou tambem servidor operacional local. A medida correta e separar responsabilidades: servidor local proprio para API e outro empacotador simples para React.
