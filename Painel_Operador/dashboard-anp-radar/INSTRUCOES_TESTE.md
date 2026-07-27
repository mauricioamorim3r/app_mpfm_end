# Radar ANP - pacote de teste local

Este pacote deve ser executado localmente no ambiente de teste, porque o Radar precisa ler pastas/arquivos do Windows, salvar configuracoes e gerar o SQLite local.

## Requisitos

- Node.js 20 ou superior.
- Python 3.11 ou superior.
- Acesso de leitura as pastas onde estao os arquivos de medicao, XML, exports ANP, cadastros, certificados e documentos.

## Instalar uma vez

Abra PowerShell dentro da pasta `dashboard-anp-radar` e rode:

```powershell
npm install
python -m pip install -r requirements.txt
```

## Rodar

```powershell
npm run app
```

Depois abra:

```text
http://127.0.0.1:6287
```

A porta padrao do Radar e `6287`, para evitar conflito com servidores antigos em `5173`.

## Configurar fontes reais

Na aplicacao, abra `Configuracao` e cole os caminhos reais do ambiente de teste. Use um caminho por linha. Pode ser pasta raiz; quando `subpastas` estiver marcado, o Radar procura tambem nas subpastas.

Depois clique em `Salvar caminhos` e `Reprocessar dashboard`.

## O que sera gerado

- `src/data/dashboard-data.json`: base consolidada usada pelo frontend.
- `data/radar-anp.sqlite`: SQLite local consultavel e auditavel.
- `data/proposal-decisions.json`: decisoes de propostas, criado somente quando houver autorizacao/rejeicao/adiamento.
- `data/ai-action-log.jsonl`: log auditavel de decisoes/acoes, criado somente quando houver acao.

O comando `npm run app` gera o frontend em `dist/` com `esbuild` e sobe o servidor local proprio do Radar. O Vite nao e mais necessario para executar a aplicacao.

## Como tratar pendencias

Existem dois caminhos:

- Corrigir a fonte: colocar/corrigir o arquivo na pasta correta e reprocessar. Este e o caminho que resolve tecnicamente a divergencia.
- Dar baixa operacional: registrar uma justificativa na aplicacao. Isso nao altera o arquivo de origem nem apaga a evidencia; apenas registra que a pendencia foi tratada/adiada/rejeitada com trilha de auditoria.

## Observacao

O pacote nao inclui `node_modules`; ele e recriado por `npm install`. Isso deixa o zip menor e mais portavel.
