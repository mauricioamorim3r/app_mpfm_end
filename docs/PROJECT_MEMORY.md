# Project Memory

## Identidade
- Nome: MPFM App
- Objetivo principal: consolidar ingestão MPFM e SEP, reconciliação, QA e exportação local.
- Ambiente: operação offline com FastAPI, SQLite, HTML/JS local e geração Excel/PDF.

## Fontes oficiais
- PDFs MPFM Daily/Hourly.
- TXTs do separador de teste.
- Cadastro local em `cadastro.json`.
- Banco local SQLite em `data/mpfm_local.db`.

## Regras críticas
- Preservar rastreabilidade entre arquivo de origem e medição consolidada.
- Não inferir conformidade ou reconciliação sem evidência.
- Diferenciar dado bruto recebido de dado curado/oficial.
- Manter sobreposições e duplicidades com resolução explícita.

## Modelo de dados alvo
- Camada `RAW`: arquivos recebidos, eventos de parsing e medições brutas.
- Camada `CURATED`: medições oficiais, issues, reconciliações, alinhamentos e cards.
- Governança: decisões de projeto e critérios operacionais persistidos.

## Pendências abertas
- Validar visualmente a interface em operação real antes de empacotar release.
- Validar upload ponta a ponta com arquivo SEP TXT real quando um exemplo estiver disponível nesta pasta.
- Validar reconciliação ponta a ponta com um dia que tenha dados horários MPFM + SEP suficientes.
- Formalizar matriz origem x destino para exportações Excel.

## Status de estabilização
- Backend dividido por domínio em `routes`, `services` e `repositories`.
- Frontend dividido em módulos por tela em `static/app.*.js`.
- Testes automatizados de parsing, reconciliação, API e UI disponíveis em `tests/`.
- Em 2026-04-27, `python -m pytest -q` passou com `288 passed`.
- Em 2026-04-27, aceitação isolada com arquivos reais validou 6 PDFs MPFM, 3 PDFs de alarmes FCS320 e 3 XML042 importados/exportados. Não havia TXT SEP real disponível nesta pasta.
- A aba `CARDS_RESUMO` foi removida dos workbooks/exportações por decisão operacional; cards permanecem disponíveis na UI/API, mas não entram mais nos arquivos Excel. A checagem real isolada confirmou Excel de produção em cerca de 35s sem essa aba.
- Em 2026-04-27, a documentação foi atualizada e o pacote de distribuição foi preparado para publicação no GitHub.

## Nunca esquecer
- Priorizar data pelo conteúdo do arquivo, não pelo nome.
- Preservar evidência de conflito e duplicidade.
- Evitar mudanças grandes em cálculo sem cobertura de validação.
- Manter PDFs de alarmes FCS320 separados da carga de produção PDF/TXT.
- Não reintroduzir aba de cards em Excel mensal ou Excel de produção sem nova decisão explícita.
