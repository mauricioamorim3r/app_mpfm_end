# Checklist de Aceite da UI

## Preparação

1. Rodar o smoke test automático:

```bash
python scripts/api_smoke_test.py
```

2. Subir a aplicação:

```bash
python server.py
```

3. Abrir no navegador:

```text
http://localhost:8765
```

4. Se existir outra instância antiga na mesma porta, reiniciar antes de validar.

## Checklist global

- A página abre sem erro visual evidente.
- O mês global carrega opções válidas.
- O botão `Atualizar` responde.
- O botão `Auto` alterna entre `ON` e `OFF`.
- Navegação lateral/topo troca de página sem travar.
- O título e subtítulo mudam conforme a tela ativa.

## Resumo

- A tela inicial carrega cards e indicadores sem erro.
- O resumo responde à troca do mês global.
- O calendário/matriz mensal exibe dados ou estado vazio coerente.
- O gráfico de desvio carrega sem erro visual.

## Upload

- A área de upload aceita seleção de arquivos.
- O fluxo de upload não quebra ao enviar arquivos reais.
- O processamento por pasta responde sem erro.
- O histórico de processamento carrega.
- Logs e mensagens de parsing aparecem de forma compreensível.

## MPFM

- A tabela carrega com os filtros padrão.
- Filtros de data, banco, tag e tipo respondem.
- O seletor de colunas abre e salva seleção.
- Edição manual de medição abre e salva sem erro.
- Export CSV e Excel funcionam a partir da tela.

## Separador

- A tabela principal carrega com filtros padrão.
- Filtros por data e banco respondem.
- A visualização de fluidos (`óleo`, `gás`, `água`) alterna corretamente.
- CRUD manual de linha SEP responde sem travar a interface.
- Alinhamentos e duplicidades abrem e carregam dados.
- Export SEP CSV e Excel funcionam.
- O botão `Excel Produção` gera arquivo válido.

## Cards

- A listagem diária carrega.
- Cards manuais podem ser criados, exibidos e excluídos.
- Prazos carregam e podem ser criados/removidos.
- Export PDF funciona.

## Gráficos

- Os gráficos carregam com o mês selecionado.
- Alterar filtros atualiza séries sem erro.
- Estados vazios aparecem de forma coerente quando não há dados.

## Alertas

- A tabela de alertas carrega.
- Contadores de severidade são preenchidos.
- Filtro por severidade responde.

## Cadastro

- A listagem carrega.
- Inclusão e edição de cadastro funcionam.
- A checagem de cobertura entre cadastro e dados processados carrega.

## Exportar

- A lista de arquivos gerados carrega.
- O download dos arquivos disponíveis funciona.

## Reconciliação

- A tela abre sem erro visual.
- A lista de execuções anteriores carrega.
- O modal/fluxo de parâmetros PVT abre corretamente.
- A execução de reconciliação com massa horária real suficiente conclui sem erro.
- O export Excel da reconciliação funciona para uma execução válida.

## Modais críticos

- Modal de PVT abre, salva e fecha corretamente.
- Modal de colunas MPFM abre e persiste seleção.
- Modal de colunas SEP abre e persiste seleção.
- Modal de manutenção/configurações abre sem quebrar o restante da UI.

## Critérios de saída

Considerar a versão pronta para operação quando:

- o smoke test automático passar
- nenhuma tela principal quebrar visualmente
- os fluxos de CRUD principais responderem
- os exports principais gerarem arquivos válidos
- a reconciliação funcionar com um conjunto real de dados suficiente
