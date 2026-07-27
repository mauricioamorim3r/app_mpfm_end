# Guia Prático de Reconciliação — MPFM Manager

## 📋 Visão Rápida

A **Reconciliação MPFM × SEP** é acessível através da interface web em:
```
http://127.0.0.1:8765 → Menu "Reconciliação"
```

Na tela atual, a área **Calibração 24h** é destinada ao fluxo **TOPSIDE vs SEPARADOR**: o MPFM Topside é comparado com a referência autorizada do separador durante uma campanha de 24h, com registro de PVT, variáveis analíticas, proposta de fator K e monitoramento pós-aplicação. A sistemática **SUBSEA vs TOPSIDE** permanece nos módulos atuais de monitoramento/comparação e não usa este novo fluxo de campanha.

---

## 🚀 Fluxo Operacional Completo - TOPSIDE vs SEPARADOR

### Passo 0: Iniciar a campanha/calibração 24h

**Onde**: Menu **"Reconciliação" → "Calibração 24h"**

**Campos de entrada da atividade**:
```
Arranjo:                 TOPSIDE vs SEPARADOR
Natureza da atividade:   Calibração periódica / comissionamento / investigação / monitoramento
Banco e TAG do medidor:  Identificação do MPFM Topside
Data de referência:      Dia da janela de 24h
Início do teste:         Data/hora operacional de início
Duração totalizada:      Normalmente 24 h
Referência metrológica:  Separador de testes / tag do vaso
P/T médias MPFM:         Condições de linha no medidor
P/T médias separador:    Condições médias do separador
Autor e notas:           Rastreabilidade da atividade
```

Ao selecionar banco, TAG e data, a aplicação consulta a base local e mostra quantas horas de **MPFM**, **Separador** e **PVT** existem para a janela. O cálculo só fica disponível quando há dados MPFM e separador para o dia escolhido.

### Passo 1: Configurar Parâmetros PVT

**Quando fazer**: Antes da primeira reconciliação de um banco/poço

**Onde**: Menu **"Reconciliação" → "Parâmetros PVT"**

**Campos Obrigatórios**:
```
┌─────────────────────────────────────────┐
│ Banco/Poço:          B03               │
│ TAG MPFM:            FI_320_001        │
│ FE (encolhimento):   0.9850            │
│ RS (solubilidade):   75.5  Sm³/Sm³     │
│ ρ óleo (standard):   870.0 kg/m³       │
│ ρ gás (standard):    1.15  kg/m³       │
│ ρ água (standard):   1015.0 kg/m³      │
│ GSV confirmado:      ☑ Sim             │
│ Modo GOR:            triphasic         │
│ Limite HC:           5.0 %             │
│ Limite Total:        5.0 %             │
│ Limite Água:         20.0 %            │
│ Válido de:           2026-04-01        │
│ Válido até:          2026-04-30        │
│ Fonte:               Análise PVT Lab   │
│ Autor:               João Silva        │
└─────────────────────────────────────────┘
```

**⚠️ Atenção Crítica**:
- **GSV confirmado = SIM**: essencial para cálculos funcionarem
- **Modo GOR**:
  - `triphasic` → comparação completa (recomendado)
  - `fixed` → bloqueia comparação de gás
  - `unknown` → bloqueia toda trilha standard

**✅ Salvar**: Parâmetro fica disponível para reconciliações futuras

---

### Passo 2: Carregar Dados SEP (Separador)

**Quando fazer**: Após testes de separador estarem disponíveis

**Onde**: Menu **"Separador" → "Carregar Dados"**

**Opções de Carga**:

#### A) Upload de Arquivo TXT
```
1. Selecionar arquivo .txt do separador
2. Sistema detecta automaticamente formato
3. Parse extrai: água (GSV/NSV), gás, GSV, BSW, pressão, temperatura
4. Valida dados e salva no banco
```

#### B) Entrada Manual
```
Campos disponíveis (por hora):
- Hora (0-23)
- Água GSV (Sm³) — PRIORIDADE 1
- Água NSV (Sm³) — alternativa
- Água massa (t) — fallback
- GSV Separador (Sm³)
- Gás volume (Sm³) — PRIORIDADE 1
- Gás massa (t) — alternativa
- BSW usuário (%)
- Pressão (bar g)
- Temperatura (°C)
```

**💡 Dica**: Preferir **água GSV** e **gás volume** quando disponíveis (maior precisão)

---

### Passo 3: Carregar Dados MPFM

**Quando fazer**: PDFs daily/hourly já processados

**Onde**: Automático após upload de PDFs via **"Upload de Relatórios"**

**Dados Extraídos dos PDFs**:
- Massas corrigidas (linha): óleo, gás, água, HC, total
- Volumes standard (@20°C): óleo, gás, água
- Condições de linha: pressão, temperatura, densidades

**Verificar Disponibilidade**:
```
Menu "MPFM" → "Medições Curadas"
- Filtrar por banco e data
- Ver resumo diário e horário
- Validar dados disponíveis
```

---

### Passo 4: Executar Reconciliação 24h

**Quando fazer**: Quando existirem dados SEP + MPFM + PVT configurado

**Onde**: Menu **"Reconciliação" → "Executar Reconciliação"**

**Tela de Execução**:
```
┌─────────────────────────────────────────┐
│ Data de Referência:  [2026-04-20]     │
│ Banco/Poço:          [B03]            │
│ TAG MPFM:            [FI_320_001]     │
│ PVT Params ID:       [auto-seleção]   │
│                                         │
│ Modo Proposta K:     ○ HC 24h         │
│                      ○ Total 24h       │
│                      ○ Manual          │
│                                         │
│ K Atual (config):    1.0000           │
│ K Proposto (calc):   1.0234  [+2.34%] │
│                                         │
│ [Executar Reconciliação]              │
└─────────────────────────────────────────┘
```

**Parâmetros**:
- **Data**: dia de referência (janela 24h)
- **Banco/TAG**: identifica qual MPFM reconciliar
- **PVT ID**: sistema busca automaticamente parâmetro válido para data
- **Modo K**: como calcular proposta de ajuste

**Resultado**:
Sistema processa 24 horas e exibe resultado consolidado

---

### Passo 5: Interpretar Resultados

**Interface de Resultados** mostra:

#### A) Resumo Trilha LINHA (Corrected)
```
╔════════════════════════════════════════════════════════╗
║ TRILHA LINHA (Massa Corrigida)                        ║
╠════════════════════════════════════════════════════════╣
║ HC (Hidrocarboneto):                                   ║
║   Referência SEP:    105.234 t                        ║
║   MPFM Medido:       102.100 t                        ║
║   Desvio:           -2.98%           🟡 ATENÇÃO       ║
╠════════════════════════════════════════════════════════╣
║ Total (HC + Água):                                     ║
║   Referência SEP:    125.678 t                        ║
║   MPFM Medido:       124.500 t                        ║
║   Desvio:           -0.94%           🟢 OK            ║
╠════════════════════════════════════════════════════════╣
║ Água:                                                  ║
║   Referência SEP:     20.444 t                        ║
║   MPFM Medido:        22.400 t                        ║
║   Desvio:           +9.57%           🟡 ATENÇÃO       ║
╠════════════════════════════════════════════════════════╣
║ Status Linha:        🟡 ATENÇÃO                       ║
╚════════════════════════════════════════════════════════╝
```

#### B) Resumo Trilha STANDARD (@20°C)
```
╔════════════════════════════════════════════════════════╗
║ TRILHA STANDARD (Volume @20°C, 1 bar)                 ║
╠════════════════════════════════════════════════════════╣
║ Óleo Standard:                                         ║
║   Referência SEP:    120.5 Sm³                        ║
║   MPFM Medido:       117.2 Sm³                        ║
║   Desvio:           -2.74%           🟡 ATENÇÃO       ║
╠════════════════════════════════════════════════════════╣
║ Gás Standard:                                          ║
║   Referência SEP:    9125.0 Sm³                       ║
║   MPFM Medido:       9056.0 Sm³                       ║
║   Desvio:           -0.76%           🟢 OK            ║
╠════════════════════════════════════════════════════════╣
║ Status Standard:     🟡 ATENÇÃO                       ║
╚════════════════════════════════════════════════════════╝
```

#### C) Status Final e Cobertura
```
╔════════════════════════════════════════════════════════╗
║ CONSOLIDADO 24 HORAS                                   ║
╠════════════════════════════════════════════════════════╣
║ Horas Válidas:       22 / 24                          ║
║ Cobertura:           91.7%                            ║
║ Status Final:        🟡 ATENÇÃO                       ║
╠════════════════════════════════════════════════════════╣
║ BSW Gap Médio:       0.35 pp          🟢 OK           ║
║ Consolidado Completo: NÃO (22h)                       ║
╚════════════════════════════════════════════════════════╝
```

#### D) Proposta de Fator K
```
╔════════════════════════════════════════════════════════╗
║ PROPOSTA DE AJUSTE (Fator K)                          ║
╠════════════════════════════════════════════════════════╣
║ Base de Cálculo:     HC 24h                           ║
║ K Atual:             1.0000                           ║
║ K Proposto:          1.0308                           ║
║ Ajuste:             +3.08%                            ║
║                                                        ║
║ Melhoria Esperada:                                     ║
║   Desvio Antes:     -2.98%                            ║
║   Desvio Depois:    ~0.00%                            ║
║   Ganho:            +2.98 pp                          ║
╠════════════════════════════════════════════════════════╣
║ Proposta Válida:     ✅ SIM                           ║
║ Dentro do Limite:    ✅ SIM (< 5%)                    ║
╚════════════════════════════════════════════════════════╝
```

#### E) Flags de QA
```
⚠️ Flags de Qualidade Detectadas:
- qa_cobertura_incompleta_22h  (2 horas ausentes)
```

---

## 📊 Interpretação de Status

### 🟢 OK
- Desvio dentro do limite configurado
- Medições confiáveis
- Nenhuma ação necessária

### 🟡 ATENÇÃO
- Desvio entre 1× e 2× o limite
- Verificar tendências ao longo de dias
- Pode indicar necessidade de ajuste K futuro

### 🔴 VERIFICAR
- Desvio > 2× o limite
- Investigar causa raiz:
  - Erro instrumental?
  - Dados SEP incorretos?
  - PVT desatualizado?
  - Condição operacional anormal?
- Considerar proposta de K (se recorrente)

### ⚪ INDISPONÍVEL
- Dados ausentes ou bloqueados
- Verificar:
  - PDFs processados?
  - Dados SEP carregados?
  - PVT configurado corretamente?
  - `gsv_confirmed = True`?

---

## 🔧 Cenários Práticos

### Cenário 1: Primeira Reconciliação (Setup Inicial)

**Situação**: Banco B03 nunca reconciliado

**Checklist**:
```
☐ 1. Configurar parâmetros PVT para B03
     - Obter FE, RS, densidades do laboratório
     - Marcar GSV confirmado = SIM
     - Definir modo GOR = triphasic
     
☐ 2. Carregar dados SEP do dia
     - Upload TXT ou entrada manual
     - Verificar 24 horas completas
     
☐ 3. Processar PDFs daily/hourly do MPFM
     - Upload via interface
     - Aguardar processamento
     
☐ 4. Executar reconciliação
     - Selecionar data e banco
     - Modo K = HC 24h
     
☐ 5. Revisar resultado
     - Status OK? → Configuração correta ✅
     - Status VERIFICAR? → Investigar PVT ou K ⚠️
```

---

### Cenário 2: Ajuste de Fator K

**Situação**: Reconciliação mostra desvio consistente de -3% em HC

**Passos**:
```
1. Confirmar tendência:
   - Executar reconciliação para 3-5 dias consecutivos
   - Verificar se desvio permanece similar
   
2. Gerar proposta K:
   - Modo = HC 24h
   - Sistema calcula K_proposto
   - Revisar melhoria esperada
   
3. Aplicar K no MPFM (físico):
   - Anotar K_atual e K_proposto
   - Aplicar ajuste no FCS320/medidor
   - Documentar em registro de calibração
   
4. Validar ajuste:
   - Aguardar próximo período de medição
   - Reconciliar novamente
   - Confirmar desvio reduzido
```

---

### Cenário 3: Diagnóstico de VERIFICAR

**Situação**: Status VERIFICAR (-12% em HC)

**Investigação**:
```
1. Verificar dados de entrada:
   ☐ Dados SEP coerentes?
      - BSW gap < 0.5 pp?
      - Volumes dentro de faixa esperada?
   
   ☐ PDFs MPFM processados corretamente?
      - Verificar em "Medições Curadas"
      - Conferir unidades
   
2. Revisar PVT:
   ☐ Parâmetros atualizados?
      - FE/RS adequados para período?
      - Densidade standard correta?
   
   ☐ GSV confirmado = SIM?
      - Se NÃO, cálculo bloqueado
   
3. Verificar condições operacionais:
   ☐ Operação normal no dia?
      - Sem paradas/testes?
      - Regime estabilizado?
   
   ☐ Alinhamento SEP correto?
      - Poço/banco correto testado?
```

---

### Cenário 4: Cobertura Incompleta

**Situação**: Apenas 18 horas válidas das 24

**Causas Possíveis**:
```
❌ Dados SEP ausentes para algumas horas
   → Solução: Carregar dados completos

❌ PDFs MPFM faltando
   → Solução: Processar hourly reports ausentes

❌ Dados MPFM com HC = NULL
   → Solução: Verificar processamento PDF

❌ Dados SEP sem água ou gás
   → Solução: Entrada manual ou fallback massa
```

**Impacto**:
- Cobertura ≥ 80% (≥20h): resultado confiável
- Cobertura < 80%: resultado parcial, revisar

---

## 📤 Exportação de Resultados

### Excel Report
**Menu**: "Reconciliação" → "Exportar Excel"

**Abas Geradas**:
1. **Resumo_24h**: consolidado linha e standard
2. **Hora_a_Hora**: detalhamento por hora
3. **Proposta_K**: cálculo e aplicabilidade
4. **Flags_QA**: lista de alertas
5. **Graficos**: visualizações de desvios

### JSON API
**Endpoint**: `POST /api/recon/calculate-24h`

**Request**:
```json
{
  "day_ref": "2026-04-20",
  "bank": "B03",
  "tag": "FI_320_001",
  "pvt_id": 15,
  "current_k_factor": 1.0000,
  "proposal_mode": "hc"
}
```

**Response**:
```json
{
  "resumo_24h": { ... },
  "horas": [ ... ],
  "proposta_k": { ... },
  "qa_flags": [ ... ]
}
```

---

## ⚙️ Configurações Avançadas

### Ajuste de Limites

**Onde**: Editar parâmetros PVT

**Quando ajustar**:
- Poço maduro: aumentar limite água (ex: 30%)
- Alta variabilidade: aumentar limite HC/Total (ex: 7%)
- Testes exploratórios: limites mais restritos (ex: 3%)

### Modo GOR Especial

**`fixed`**: Usar quando GOR conhecido e constante
- Bloqueia comparação gás standard
- Foca validação em óleo

**`zero`**: Usar para poços sem gás livre
- Similar a `fixed`
- Simplifica reconciliação

**`unknown`**: Usar temporariamente
- Bloqueia trilha standard inteira
- Mantém apenas trilha linha operacional

### Versionamento PVT

**Boas Práticas**:
```
- Criar novo registro PVT a cada campanha
- Definir valid_from e valid_to
- Documentar fonte (análise lab, campanha N)
- Marcar autor e data
- Nunca deletar registros antigos (histórico)
```

---

## 🐛 Troubleshooting

### Problema: "Erro ao executar reconciliação"

**Possíveis Causas**:
1. PVT não encontrado para data
   → Verificar `valid_from` / `valid_to`
   
2. Dados SEP ausentes
   → Carregar dados do separador
   
3. Dados MPFM ausentes
   → Processar PDFs hourly

4. Banco/TAG não corresponde
   → Verificar nomenclatura

### Problema: Todos status INDISPONÍVEL

**Checklist**:
```
☐ gsv_confirmed = True no PVT?
☐ FE, RS, densidades preenchidos?
☐ Dados SEP tem água e gás?
☐ PDFs MPFM processados com sucesso?
```

### Problema: Proposta K não aparece

**Causas**:
1. `current_k_factor` não informado
   → Digitar K atual do medidor
   
2. Desvio é zero
   → Proposta desnecessária
   
3. Dados insuficientes
   → Menos de 20 horas válidas

### Problema: Gap BSW alto (> 0.5 pp)

**Significado**: Inconsistência água/BSW nos dados SEP

**Ação**:
- Verificar entrada SEP
- Confirmar BSW informado correto
- Não bloqueia cálculo, mas gera flag atenção

---

## 📚 Referências Técnicas

### Documentos Relacionados
- **`RECONCILIACAO_REGRAS_LOGICA.md`**: Especificação técnica completa
- **`recon_engine.py`**: Código-fonte do motor de cálculo
- **`routes/recon_routes.py`**: API REST da reconciliação
- **PE-02 Memorial Ajustado**: Metodologia de referência

### Tabelas do Banco de Dados
- **`pvt_params`**: Parâmetros PVT versionados
- **`sep_hourly_data`**: Dados horários do separador
- **`measurements_curated`**: Medições MPFM processadas
- **`recon_executions`**: Histórico de reconciliações

---

## ✅ Checklist Operacional Rápido

### Antes de Reconciliar:
```
☑ PVT configurado para banco/TAG
☑ PVT com gsv_confirmed = True
☑ PVT válido para data desejada
☑ Dados SEP carregados (água + gás + GSV)
☑ PDFs MPFM processados (daily + hourly)
☑ K_atual do medidor anotado (se proposta K)
```

### Durante Análise:
```
☑ Status não é INDISPONÍVEL
☑ Cobertura ≥ 80% (≥ 20h válidas)
☑ Gap BSW ≤ 0.5 pp
☑ Desvios coerentes entre linha e standard
☑ Flags QA revisadas e compreendidas
```

### Após Resultado OK:
```
☑ Documentar resultado em log operacional
☑ Se VERIFICAR: investigar causa raiz
☑ Se proposta K: avaliar aplicabilidade
☑ Exportar Excel para arquivo
```

---

**Guia Prático** — MPFM Manager v4.1  
**Última Atualização**: 28/04/2026  
**Para dúvidas técnicas**: consultar `RECONCILIACAO_REGRAS_LOGICA.md`
