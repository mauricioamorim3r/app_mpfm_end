# Manifesto de arquivos da aplicacao Radar ANP

A aplicacao fica somente na pasta `dashboard-anp-radar`.

Nao e necessario levar os arquivos soltos da pasta acima (`Painel_Operador`), pois eles sao documentos, XMLs, planilhas e dados fonte usados para teste/ingestao.

## Levar para outro computador

Copie estes itens da pasta `dashboard-anp-radar`:

- `config/`
- `data/`
- `docs/`
- `public/`
- `server/`
- `scripts/`
- `src/`
- `templates/`
- `index.html`
- `INSTRUCOES_TESTE.md`
- `MANIFESTO_ARQUIVOS_APLICACAO.md`
- `package.json`
- `package-lock.json`
- `requirements.txt`
- `start-radar-anp.bat`

O servidor local fica em `server/` e o build do frontend fica em `scripts/build_frontend.mjs`.

Documentos importantes adicionados na migracao para o MPFM:

- `docs/RADAR_ANP_PLANO_MESTRE.md`: contrato operacional do Radar ANP inteligente.
- `docs/RADAR_ANP_TEMPLATE_GERAL_INGESTAO.md`: definicao do template geral de ingestao.
- `templates/Radar_ANP_Template_Geral_Ingestao.xlsx`: modelo manual/contingencia para ingestao e auditoria.

## Nao precisa levar

- `node_modules/`: recriado com `npm install`.
- `release/`: contem zips gerados; leve apenas se quiser transportar o pacote pronto.
- `.playwright-mcp/`: temporario de teste, se existir.
- `dist/`: opcional. E gerado por `npm run build` ou `npm run app`; pode ser recriado.

## Atenção a chaves e dados locais

- `config/ai-settings.local.json` pode conter chaves de API se elas forem cadastradas. Antes de compartilhar com terceiros, conferir/remover chaves.
- `data/radar-anp.sqlite` e `src/data/dashboard-data.json` sao dados consolidados gerados. Pode levar para abrir com uma base inicial, mas no ambiente de teste o ideal e configurar as fontes reais e clicar em `Reprocessar dashboard`.
- `data/evidence_text_cache.json` e apenas cache de textos extraidos; pode ser levado ou apagado. Se apagado, sera recriado.

## Dados fonte

Os dados fonte ficam fora da aplicacao: planilhas ANP, XMLs, PDFs, certificados, pastas diarias, relatorios etc. No outro computador, informe os caminhos reais desses arquivos na tela `Configuracao`.

No MPFM integrado, a pasta oficial do modulo e `C:\MPFM\NOVO\Painel_Operador\dashboard-anp-radar`; nao sobrescrever `config/data-sources.json` com uma versao antiga apontando para OneDrive.
