# Painel Operador - Dashboard Principal

## 📋 Requisitos do Usuário

Quando o usuário acessar o **Painel Operador**, a tela principal (aba "Visão Geral") deve mostrar prioritariamente:

### 1. 📊 **Gráfico do Mês Vigente de Produção**
- Série temporal com dados diários do mês atual (julho/2026)
- **Variáveis disponíveis** (usuário seleciona quais ficam visíveis):
  - Volume de óleo (fiscal, ANP, MPFM)
  - Volume de gás
  - BSW (%)
  - HC (hidrocarboneto)
  - Vazão
- **Sobreposição de limites**:
  - Faixa calibrada (min/max)
  - PAM (Ponto de Ajuste da Medição)
- Controles: checkboxes para variáveis, select para limites

### 2. 📑 **Tabela: Comparação Fiscal x MPFM (Mês Vigente)**
- Dados do mês corrente
- Colunas: Data, Tag, Família, Fiscal, MPFM, Delta (%), Status
- Filtros: família, tag, tipo de medição
- Ordenação por delta descendente (maiores diferenças primeiro)
- Destaque visual para deltas > 5%

### 3. 🔥 **Tabela: Balanço de Gás Diário**
- Dados diários do mês corrente
- Colunas: Data, Entrada, Saída, Consumo, Flare, Balanço, Desvio (%)
- Totais acumulados no rodapé
- Destaque para dias com desvio > 3%

### 4. ⚠️ **Quadro: NFSMs Abertas** (Notificações de Falha do Sistema de Medição)
- Lista de falhas sem parecer da ANP
- Colunas: Código da Falha, Data Ocorrência, Tag, Tipo, Dias Abertos
- **Lógica de identificação**:
  - Arquivo `Falha de Medição.xlsx` = todas as falhas registradas (90 total)
  - Arquivo `Parecer.xlsx` = falhas com parecer "Aprovada" ou "Retificada" (51 total)
  - **NFSM Aberta** = código da falha NÃO aparece no arquivo Parecer (39 abertas)
- Badge vermelho com contador de pendências
- Ordenação: mais antigas primeiro

### 5. 🚨 **Alertas de Dados Faltantes**
- Banner informativo no topo se:
  - Não há dados do mês corrente
  - Faltam dados de dias recentes (últimos 3 dias)
  - Não há comparação fiscal x MPFM disponível
  - Balanço de gás incompleto

---

## 🎯 Estrutura Proposta

```
┌─────────────────────────────────────────────────────────────┐
│ 🚨 [Banner de Alerta - se dados faltantes]                  │
└─────────────────────────────────────────────────────────────┘

┌───────────────────────────┬─────────────────────────────────┐
│ 📊 Gráfico Produção Mês   │ ⚠️ NFSMs Abertas (39)           │
│                           │ ┌─────────────────────────────┐ │
│ [Controles: variáveis +   │ │ BACALHAU 2026.051 - 3 dias  │ │
│  limites]                 │ │ BACALHAU 2026.048 - 5 dias  │ │
│                           │ │ BACALHAU 2026.047 - 7 dias  │ │
│ [Gráfico Chart.js]        │ │ ...                         │ │
│                           │ └─────────────────────────────┘ │
└───────────────────────────┴─────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 📑 Comparação Fiscal x MPFM - Julho/2026                    │
│ [Filtros: Família | Tag | Tipo]                             │
│ ┌──────┬──────┬────────┬─────────┬─────────┬───────┬──────┐│
│ │ Data │ Tag  │Família │ Fiscal  │  MPFM   │ Delta │Status││
│ ├──────┼──────┼────────┼─────────┼─────────┼───────┼──────┤│
│ │07/07 │20FT..│ a001   │ 9.998   │ 9.820   │ -1.8% │ OK   ││
│ │ ...  │ ...  │ ...    │   ...   │   ...   │  ...  │ ...  ││
│ └──────┴──────┴────────┴─────────┴─────────┴───────┴──────┘│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 🔥 Balanço de Gás Diário - Julho/2026                       │
│ ┌──────┬─────────┬─────────┬─────────┬───────┬─────────┬───┐│
│ │ Data │ Entrada │  Saída  │ Consumo │ Flare │ Balanço │ % ││
│ ├──────┼─────────┼─────────┼─────────┼───────┼─────────┼───┤│
│ │07/01 │ 137.524 │ 135.000 │  2.000  │  500  │  24     │0.2││
│ │ ...  │   ...   │   ...   │   ...   │  ...  │  ...    │...││
│ └──────┴─────────┴─────────┴─────────┴───────┴─────────┴───┘│
│ TOTAIS: Entrada: 4.234.567 | Balanço: +234 (0.5%)           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementação Técnica

### Backend (APIs necessárias)

1. **GET `/api/painel-operador/nfsm-abertas`**
   - Lê `Painel_Operador/Falha de Medição.xlsx` + `Painel_Operador/Parecer.xlsx`
   - Retorna falhas sem parecer
   - Campos: `codigo_falha`, `data_ocorrencia`, `tag`, `tipo`, `dias_abertos`

2. **GET `/api/painel-operador/comparacao-mensal`** *(verificar se existe)*
   - Filtra dados do mês corrente
   - Retorna comparação fiscal x MPFM por tag/dia

3. **GET `/api/painel-operador/gas-balance-mensal`** *(já existe em `/gas-balance`)*
   - Adaptar para retornar apenas mês corrente
   - Incluir totais acumulados

4. **GET `/api/painel-operador/producao-mensal-grafico`**
   - Dados diários do mês para gráfico
   - Todas as variáveis (óleo, gás, BSW, HC, vazão)
   - Incluir limites cadastrados (faixa calibrada, PAM)

### Frontend (JavaScript)

1. **Modificar `renderPainelOperadorOverview()`**
   - Reorganizar layout para priorizar os 4 elementos principais
   - Mover informações técnicas (inventário, staging) para seção secundária

2. **Criar funções de renderização**:
   - `renderPoProductionChart()` - Gráfico Chart.js com variáveis e limites
   - `renderPoComparisonTable()` - Tabela comparação fiscal x MPFM
   - `renderPoGasBalanceTable()` - Tabela balanço de gás
   - `renderPoNfsmPanel()` - Quadro de NFSMs abertas

3. **Controles interativos**:
   - Checkboxes para variáveis do gráfico
   - Select para limites (faixa calibrada, PAM)
   - Filtros nas tabelas (família, tag, período)

---

## 📊 Estado Atual vs. Desejado

### ✅ O que já existe:
- API `/gas-balance` (balanço de gás)
- API `/ihm-reports` (dados IHM)
- Aba "Comparação" com tabela fiscal x MPFM (mas não na view principal)
- Aba "IHM Reports" com relatórios (mas não na view principal)
- Cards de resumo (6 KPIs no topo)

### ❌ O que precisa ser criado:
- API `/nfsm-abertas` (leitura dos arquivos Excel)
- API `/producao-mensal-grafico` (dados para gráfico)
- Reorganização da aba "Visão Geral" priorizando os 4 elementos
- Gráfico interativo de produção com Chart.js
- Alertas visuais de dados faltantes

### 🔄 O que precisa ser movido:
- Tabela de comparação (da aba "Comparação" para a view principal)
- Balanço de gás (da aba "IHM Reports" para a view principal)

---

## 📁 Arquivos de Dados

### NFSMs
- **Falha de Medição.xlsx**: `Painel_Operador\Falha de Medição.xlsx`
  - 90 registros totais
  - Coluna chave: `Código da Falha` (ex: BACALHAU 2026.016)
  - Outras colunas: Data Ocorrência, Tag, Tipo de Notificação, Tipo de Falha, etc.

- **Parecer.xlsx**: `Painel_Operador\Parecer.xlsx`
  - 51 registros com parecer
  - Coluna chave: `Código da Falha`
  - Coluna `Parecer do Gestor`: "Aprovada" ou "Retificada"

### Cálculo de NFSMs Abertas
```python
todas_falhas = set(df_falhas['Código da Falha'])  # 90 códigos
com_parecer = set(df_parecer['Código da Falha'])   # 51 códigos
nfsm_abertas = todas_falhas - com_parecer          # 39 códigos pendentes
```

---

## 🎨 Diretrizes de UI

1. **Hierarquia Visual**:
   - Elementos operacionais prioritários (gráfico, tabelas, NFSMs) = cards grandes, destaque
   - Informações técnicas (inventário, staging) = seção secundária, abaixo

2. **Cores de Status**:
   - Verde: OK, dentro dos limites
   - Amarelo: Atenção, desvio 3-5%
   - Vermelho: Crítico, desvio > 5% ou NFSM aberta há > 30 dias

3. **Responsividade**:
   - Desktop: layout 2 colunas (gráfico + NFSMs, tabelas full-width)
   - Mobile: empilhamento vertical, tabelas com scroll horizontal

---

## 📝 Próximos Passos

1. ✅ Análise de requisitos e estrutura de dados (concluído)
2. ⏳ Criar backend API `/nfsm-abertas` em Python/Flask
3. ⏳ Criar backend API `/producao-mensal-grafico`
4. ⏳ Adaptar `/gas-balance` para filtro mensal
5. ⏳ Adaptar dados de comparação para API mensal
6. ⏳ Implementar novo layout da aba "Visão Geral"
7. ⏳ Criar gráfico interativo com Chart.js
8. ⏳ Implementar tabelas de comparação e balanço de gás
9. ⏳ Implementar painel de NFSMs abertas
10. ⏳ Testar e ajustar com dados reais
