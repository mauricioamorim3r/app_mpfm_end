# Relatório de revisão — atualizado em 13/08/2026

## Escopo implementado

- Unicidade absoluta do XML 042 por `data de produção + código ANP do poço`.
- Registro SQLite persistente e oculto no Windows, independente do nome e da pasta do XML.
- Histórico inicial com nove XMLs reais fornecidos em 12/08/2026 e importação configurável de diretórios antigos.
- Conflito entre dois XMLs históricos do mesmo dia + poço bloqueia novas emissões.
- Registro de tentativas geradas, bloqueadas e malsucedidas.
- Bloqueio de duplicidade na Base Única; nenhuma linha é escolhida silenciosamente.
- Validação de CNPJ raiz com exatamente oito dígitos.
- Correção PE‑02 `18FT0506` × Riser P2 `13FT0217`.
- Convenção explícita de desvio: `(MPFM corrigido − referência) / referência × 100`.
- Separação das linhas de base de plausibilidade Daily e Hourly.
- Supressão do percentual para referência inferior a 0,1 t.
- Valores sem arredondamento, unidade e fórmula explícita no comparativo de pares.
- Remoção da matriz `COMPARATIVO_SEP_LIVRE` e de qualquer vínculo automático de alinhamento.
- TXT do Separador preservado como fonte independente; comparação MPFM × SEP ocorre apenas no HTML, sob seleção do usuário, com exportação CSV compatível com Excel.
- CEP mensal no HTML, com filtros por mês, par e métricas; limites ±10% HC e ±7% Total.
- Redesenho efetivo do HTML com navegação lateral, filtros sempre visíveis, seis KPIs, cartões dos três pares físicos, painéis Topside/Subsea/Separador independentes e tabela detalhada.
- Nova tela `Cadeia do dado`, com aquisição, Separador, contexto PI, Base Única, cálculos e publicação, preenchida somente com dados já existentes.
- Indicadores sem fonte disponível exibem `Sem dado`; códigos de status do PI não são classificados como alarmes sem mapa de estados versionado.
- Comparações com referência próxima de zero são apresentadas como `Suprimido`, sem percentual enganoso.

## Validação executada

- 20 testes automatizados aprovados.
- Todos os arquivos Python compilados.
- 974 desvios Subsea × Topside confrontados contra recálculo independente: diferença máxima 0,0 ponto percentual.
- 716 desvios HC e 716 desvios Total MPFM × SEP confrontados: diferença máxima 0,0 ponto percentual.
- A Base real passou a produzir os três pares: PE‑02 × P2, PE‑04 × P5 e PW‑104 × P4.
- HTML de uma janela de um dia carregou seis dias disponíveis de agosto no CEP mensal.
- Manifesto Excel → HTML aprovado e todos os blocos JavaScript passaram na verificação sintática.
- Navegação, filtros, cartões e tela de rastreabilidade conferidos no navegador; sem transbordamento horizontal no viewport desktop avaliado.

## Limite da trava de unicidade

O padrão impede duplicidade por usuário/computador. Para impedir emissão duplicada por usuários em computadores diferentes, configure `registry_path` no `config_xml042_standalone.json` para um caminho corporativo compartilhado, protegido e sujeito a backup.

## Limite de validação regulatória

A estrutura e os números do XML são validados internamente. A validação formal contra o `042.xsd` oficial permanece dependente do fornecimento e versionamento do XSD aprovado.
