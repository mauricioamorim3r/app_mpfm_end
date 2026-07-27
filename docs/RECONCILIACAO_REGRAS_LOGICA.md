# Reconciliação MPFM × SEP — Regras e Lógica Completa

## 📋 Índice
1. [Visão Geral](#visão-geral)
2. [Conceitos Fundamentais](#conceitos-fundamentais)
3. [Fluxo de Cálculo](#fluxo-de-cálculo)
4. [Parâmetros PVT](#parâmetros-pvt)
5. [Hierarquia de Fontes de Dados](#hierarquia-de-fontes-de-dados)
6. [Cálculos Hora a Hora](#cálculos-hora-a-hora)
7. [Consolidação 24 Horas](#consolidação-24-horas)
8. [Regras de Status e Limites](#regras-de-status-e-limites)
9. [Flags de QA](#flags-de-qa)
10. [Proposta de Fator K](#proposta-de-fator-k)

---

## 🎯 Visão Geral

A **reconciliação** é o processo de **comparação** entre:
- **MPFM** (Multiphase Flow Meter) — medidor multifásico instalado no campo
- **SEP** (Separador de Teste) — separador trifásico de referência

O objetivo é **validar a acurácia do MPFM** usando o separador como padrão de referência, e **gerar propostas de ajuste** (fator K) quando necessário.

### Metodologia
- **Referência Técnica**: PE-02 Memorial Ajustado + Anexo de Implementação
- **Condições de Referência**: 20°C / 1,01325 bar(a)
- **Motor de Cálculo**: `recon_engine.py` — puro Python, sem dependências de banco
- **Nota Importante**: Não reproduz o cálculo interno do FCS320/MPFM

---

## 🧩 Conceitos Fundamentais

### Duas Trilhas de Comparação

#### 1. **Trilha LINHA** (Corrected)
Compara massas em **condições de linha** (corrected):
- **HC** (Hidrocarboneto) = Óleo + Gás
- **Total** = HC + Água
- **Água**

Usa dados **corrigidos** do MPFM (`oleo_corr_t`, `gas_corr_t`, `agua_corr_t`)

#### 2. **Trilha STANDARD** (@20°C, 1 bar)
Compara volumes/massas em **condições padrão**:
- **Óleo Standard** (Sm³)
- **Gás Standard** (Sm³)
- **Água Standard** (Sm³)

Usa dados **standard** do MPFM (`oleo_st_m3`, `gas_st_ksm3`, `agua_st_m3`)

### Desvio Percentual
```
Desvio (%) = [(MPFM - REF) / REF] × 100
```
- **Positivo**: MPFM mediu MAIS que o separador
- **Negativo**: MPFM mediu MENOS que o separador

---

## 🔄 Fluxo de Cálculo

```
┌─────────────────┐        ┌─────────────────┐
│  Dados SEP      │        │  Dados MPFM     │
│  (Separador)    │        │  (Medidor)      │
└────────┬────────┘        └────────┬────────┘
         │                          │
         ├─> Água (GSV/NSV/massa)   │
         ├─> GSV óleo/líquido       │
         ├─> Gás livre              │
         │                          │
         ▼                          ▼
┌─────────────────────────────────────────────┐
│        Parâmetros PVT (por Banco/TAG)       │
│  - FE (Fator Encolhimento)                  │
│  - RS (Razão Solubilidade)                  │
│  - Densidades Standard (ρ)                  │
│  - Limites de Alerta                        │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│      CÁLCULO HORA A HORA (24 horas)         │
│  1. Roteamento de fontes (água, gás)        │
│  2. Cálculo óleo base (GSV - água)          │
│  3. Transformação PVT                       │
│  4. Cálculo massas de referência            │
│  5. Comparação linha vs linha               │
│  6. Comparação standard vs standard         │
│  7. Geração de status e flags QA            │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│       CONSOLIDAÇÃO 24 HORAS                 │
│  - Soma horas válidas                       │
│  - Desvios consolidados                     │
│  - Status final                             │
│  - Cobertura temporal                       │
│  - Proposta fator K                         │
└─────────────────────────────────────────────┘
```

---

## 🧪 Parâmetros PVT

### Estrutura `PVTParams`

Parâmetros versionados por **banco/TAG**, armazenados em `pvt_params` (SQLite).

| Campo | Tipo | Descrição | Default |
|-------|------|-----------|---------|
| `bank` | str | Banco/poço (ex: B03, B08, B13) | — |
| `tag` | str | TAG do MPFM (ex: FI_320_001) | — |
| `fe` | float | Fator de encolhimento (adimensional) | — |
| `rs` | float | Razão de solubilidade (Sm³ gás / Sm³ óleo) | — |
| `rho_oleo_std` | float | Densidade óleo standard (kg/m³) | — |
| `rho_gas_std` | float | Densidade gás standard (kg/m³) | — |
| `rho_agua_std` | float | Densidade água standard (kg/m³) | — |
| `temp_ref_c` | float | Temperatura referência (°C) | 20.0 |
| `pres_ref_bar` | float | Pressão referência (bar a) | 1.01325 |
| `gsv_confirmed` | bool | GSV do óleo confirmado como gross liquid | False |
| `gor_mode` | str | Modo GOR: fixed \| zero \| triphasic \| unknown | unknown |
| `limite_hc_pct` | float | Limite alerta HC (%) | 5.0 |
| `limite_total_pct` | float | Limite alerta Total (%) | 5.0 |
| `limite_agua_pct` | float | Limite alerta Água (%) | 20.0 |
| `valid_from` | str | Data início validade (ISO) | — |
| `valid_to` | str | Data fim validade (ISO) | — |
| `source` | str | Fonte dos parâmetros | — |
| `author` | str | Autor/responsável | — |
| `notes` | str | Observações | — |

### Campos Críticos

#### `gsv_confirmed` (boolean)
- **True**: GSV do SEP é confirmado como volume bruto de líquido (óleo + água)
  - Permite calcular: `óleo_base = GSV - água`
- **False**: GSV não confirmado
  - **Bloqueia** cálculo de óleo base
  - Adiciona flag `qa_gsv_unconfirmed`

#### `gor_mode` (string)
Controla como o sistema trata a razão gás/óleo:
- **`triphasic`**: Usa separação trifásica completa
  - Compara óleo e gás standard separadamente
- **`fixed`**: GOR fixo conhecido
  - Compara apenas óleo standard
  - **Bloqueia** comparação de gás
- **`zero`**: Sem gás livre
  - Similar a `fixed`, bloqueia comparação de gás
- **`unknown`**: Modo GOR desconhecido
  - **Bloqueia** todas comparações standard
  - Adiciona flag `qa_gor_mode_unknown`

---

## 📊 Hierarquia de Fontes de Dados

### 1. Água do Separador (Prioridade Decrescente)

```python
# PRIORIDADE 1: GSV da água (volume standard do TXT)
if agua_gsv_sm3 disponível:
    usar agua_gsv_sm3
    fonte = 'gsv'

# PRIORIDADE 2: NSV da água (net standard volume, aceito se BSW=0)
elif agua_nsv_sm3 disponível:
    usar agua_nsv_sm3
    fonte = 'nsv'
    flag: 'qa_agua_nsv_usado'

# PRIORIDADE 3: Massa → Volume (fallback)
elif agua_mass_t e rho_agua_std disponíveis:
    agua_sm3 = (agua_mass_t × 1000) / rho_agua_std
    fonte = 'mass_fallback'
    flag: 'qa_water_from_mass_fallback'

# BLOQUEIO: Sem dados
else:
    agua_sm3 = None
    fonte = 'blocked'
    flag: 'qa_agua_ausente'
```

### 2. Gás Livre do Separador

```python
# PRIORIDADE 1: Volume standard direto
if gas_vol_sm3 disponível:
    usar gas_vol_sm3
    fonte = 'vol_direto'

# PRIORIDADE 2: Massa → Volume
elif gas_mass_t e rho_gas_std disponíveis:
    gas_sm3 = (gas_mass_t × 1000) / rho_gas_std
    fonte = 'mass_fallback'
    flag: 'qa_gas_from_mass_fallback'

# BLOQUEIO: Sem dados
else:
    gas_sm3 = None
    fonte = 'blocked'
    flag: 'qa_gas_ausente'
```

### 3. Óleo Base (Requer `gsv_confirmed = True`)

```python
if NOT gsv_confirmed:
    oleo_base = None
    gsv_oleo_bloqueado = True
    flag: 'qa_gsv_unconfirmed'

elif gsv_sep_sm3 e agua_sep_sm3 disponíveis:
    oleo_base_sm3 = gsv_sep_sm3 - agua_sep_sm3

else:
    oleo_base = None
    gsv_oleo_bloqueado = True
    flag: 'qa_gsv_ou_agua_ausente'
```

---

## ⚙️ Cálculos Hora a Hora

### Etapa 1: Roteamento de Fontes
Aplica hierarquias de fontes descritas acima para água, gás e óleo.

### Etapa 2: BSW (Basic Sediments and Water)

```python
# BSW Calculado
BSW_calc (%) = (agua_sep_sm3 / gsv_sep_sm3) × 100

# QA Gap BSW
if bsw_user_pct e bsw_calc_pct disponíveis:
    qa_gap_bsw_pp = |bsw_user_pct - bsw_calc_pct|
    
    if qa_gap_bsw_pp ≤ 0.5:
        flag_bsw = 'OK'
    else:
        flag_bsw = 'ATENÇÃO'
else:
    flag_bsw = 'INDISPONÍVEL'
```

### Etapa 3: Trilha PVT

#### Transformação do Óleo
```python
# Óleo standard (condições de referência)
oleo_std_reconc_sm3 = oleo_base_sm3 × FE

# Gás dissolvido no óleo
gas_dissolvido_sm3 = oleo_std_reconc_sm3 × RS
```

#### Gás Total
```python
gas_total_reconc_sm3 = gas_livre_sep_sm3 + gas_dissolvido_sm3
```

### Etapa 4: Massas de Referência

```python
# Conversão volume → massa usando densidades standard
massa_oleo_ref_t = oleo_std_reconc_sm3 × rho_oleo_std / 1000
massa_gas_ref_t  = gas_total_reconc_sm3 × rho_gas_std / 1000
massa_agua_ref_t = agua_sep_sm3 × rho_agua_std / 1000

# Agregações
massa_hc_ref_t    = massa_oleo_ref_t + massa_gas_ref_t
massa_total_ref_t = massa_hc_ref_t + massa_agua_ref_t
```

### Etapa 5: Desvios Trilha LINHA

```python
# Comparação massa corrigida (condição linha)
desvio_hc_linha_pct = [(mpfm.hc_corr_t - massa_hc_ref_t) / massa_hc_ref_t] × 100

desvio_total_linha_pct = [(mpfm.total_corr_t - massa_total_ref_t) / massa_total_ref_t] × 100

desvio_agua_linha_pct = [(mpfm.agua_corr_t - massa_agua_ref_t) / massa_agua_ref_t] × 100
```

### Etapa 6: Desvios Trilha STANDARD

```python
# Se gor_mode = 'fixed' ou 'zero':
if gor_fixed:
    desvio_oleo_st_pct = [(mpfm.oleo_st_m3 - oleo_std_reconc_sm3) / oleo_std_reconc_sm3] × 100
    desvio_gas_st_pct  = None  # BLOQUEADO
    flag: 'qa_gor_fixed_caution'

# Se gor_mode = 'unknown':
elif gor_mode == 'unknown':
    desvio_oleo_st_pct = None  # BLOQUEADO
    desvio_gas_st_pct  = None  # BLOQUEADO
    flag: 'qa_gor_mode_unknown'

# Se gor_mode = 'triphasic' (normal):
else:
    desvio_oleo_st_pct = [(mpfm.oleo_st_m3 - oleo_std_reconc_sm3) / oleo_std_reconc_sm3] × 100
    
    gas_mpfm_sm3 = mpfm.gas_st_ksm3 × 1000  # kSm³ → Sm³
    desvio_gas_st_pct = [(gas_mpfm_sm3 - gas_total_reconc_sm3) / gas_total_reconc_sm3] × 100
```

### Etapa 7: Status da Hora

```python
# Status Linha
status_linha = _status(desvio_hc_linha_pct, limite_hc_pct)
if status_linha == 'OK':
    status_linha = _status(desvio_total_linha_pct, limite_total_pct)

# Status Standard
status_oleo_st = _status(desvio_oleo_st_pct, limite_hc_pct)
status_gas_st  = _status(desvio_gas_st_pct, limite_total_pct)
status_standard = max(status_oleo_st, status_gas_st)  # pior dos dois

# Status Final da Hora
status_final = max(status_linha, status_standard)  # pior entre linha e standard

# Ranking de severidade
# 'VERIFICAR' > 'ATENÇÃO' > 'OK' > 'INDISPONÍVEL'
```

### Etapa 8: Hora Válida

```python
# Hora considerada válida se tiver pelo menos:
hora_valida = (agua_sep_sm3 disponível) AND (mpfm.hc_corr_t disponível)
```

---

## 📅 Consolidação 24 Horas

### Etapa 1: Filtragem de Horas Válidas

```python
horas_validas = [hora for hora in resultados if hora.hora_valida]
cobertura_pct = (len(horas_validas) / 24) × 100
consolidado_completo = (len(horas_validas) == 24)
```

### Etapa 2: Somatórias

```python
# Referência (separador + PVT)
massa_hc_ref_24h    = Σ massa_hc_ref_t    (horas válidas)
massa_total_ref_24h = Σ massa_total_ref_t (horas válidas)
massa_agua_ref_24h  = Σ massa_agua_ref_t  (horas válidas)
oleo_std_ref_24h    = Σ oleo_std_reconc_sm3 (horas válidas)
gas_total_ref_24h   = Σ gas_total_reconc_sm3 (horas válidas)
agua_ref_24h        = Σ agua_sep_sm3 (horas válidas)

# MPFM (medidor)
massa_hc_mpfm_24h    = Σ mpfm.hc_corr_t    (horas válidas)
massa_total_mpfm_24h = Σ mpfm.total_corr_t (horas válidas)
massa_agua_mpfm_24h  = Σ mpfm.agua_corr_t  (horas válidas)
oleo_st_mpfm_24h     = Σ mpfm.oleo_st_m3   (horas válidas)
gas_st_mpfm_24h      = Σ mpfm.gas_st_ksm3  (horas válidas)
agua_st_mpfm_24h     = Σ mpfm.agua_st_m3   (horas válidas)
```

### Etapa 3: Desvios Consolidados

```python
# Trilha LINHA
desvio_hc_24h    = [(massa_hc_mpfm_24h - massa_hc_ref_24h) / massa_hc_ref_24h] × 100
desvio_total_24h = [(massa_total_mpfm_24h - massa_total_ref_24h) / massa_total_ref_24h] × 100
desvio_agua_24h  = [(massa_agua_mpfm_24h - massa_agua_ref_24h) / massa_agua_ref_24h] × 100

# Trilha STANDARD
desvio_oleo_st_24h = [(oleo_st_mpfm_24h - oleo_std_ref_24h) / oleo_std_ref_24h] × 100

if gor_mode == 'fixed' or 'zero':
    desvio_gas_st_24h = None  # BLOQUEADO
else:
    gas_st_mpfm_sm3 = gas_st_mpfm_24h × 1000  # kSm³ → Sm³
    desvio_gas_st_24h = [(gas_st_mpfm_sm3 - gas_total_ref_24h) / gas_total_ref_24h] × 100

desvio_agua_st_24h = [(agua_st_mpfm_24h - agua_ref_24h) / agua_ref_24h] × 100
```

### Etapa 4: Status Consolidado

```python
# Trilha LINHA
status_hc    = _status(desvio_hc_24h, limite_hc_pct)
status_total = _status(desvio_total_24h, limite_total_pct)
status_agua  = _status(desvio_agua_24h, limite_agua_pct)
status_linha = max(status_hc, status_total)

# Trilha STANDARD
status_oleo_st = _status(desvio_oleo_st_24h, limite_hc_pct)
status_gas_st  = _status(desvio_gas_st_24h, limite_total_pct)
status_agua_st = _status(desvio_agua_st_24h, limite_agua_pct)
status_standard = max(status_oleo_st, status_gas_st)

# Status Final 24h
status_final_24h = max(status_linha, status_standard)
```

### Etapa 5: QA Consolidado

```python
# Gap BSW médio
qa_gap_bsw_medio_pp = média(qa_gap_bsw_pp de horas válidas)

if qa_gap_bsw_medio_pp ≤ 0.5:
    flag_bsw_consolidado = 'OK'
elif qa_gap_bsw_medio_pp disponível:
    flag_bsw_consolidado = 'ATENÇÃO'
else:
    flag_bsw_consolidado = 'INDISPONÍVEL'

# Flags consolidadas
qa_flags_consolidados = união de todas as flags das 24 horas

if cobertura < 100%:
    adicionar flag: 'qa_cobertura_incompleta_Xh'
```

---

## 🚦 Regras de Status e Limites

### Função `_status(desvio, limite)`

```python
def _status(desvio: float, limite: float) -> str:
    if desvio is None:
        return 'INDISPONÍVEL'
    
    abs_desvio = |desvio|
    
    if abs_desvio ≤ limite:
        return 'OK'
    
    elif abs_desvio ≤ (limite × 2):
        return 'ATENÇÃO'
    
    else:  # abs_desvio > (limite × 2)
        return 'VERIFICAR'
```

### Exemplos Práticos

#### Exemplo 1: HC com limite 5%
| Desvio | Status |
|--------|--------|
| +2% | OK |
| -4% | OK |
| +7% | ATENÇÃO |
| -9% | ATENÇÃO |
| +12% | VERIFICAR |
| -15% | VERIFICAR |

#### Exemplo 2: Total com limite 5%
| Desvio | Status |
|--------|--------|
| ≤ 5% | OK |
| 5% < desvio ≤ 10% | ATENÇÃO |
| > 10% | VERIFICAR |

#### Exemplo 3: Água com limite 20%
| Desvio | Status |
|--------|--------|
| ≤ 20% | OK |
| 20% < desvio ≤ 40% | ATENÇÃO |
| > 40% | VERIFICAR |

### Ranking de Severidade

Quando há múltiplos status, sempre prevalece o **mais severo**:

```
VERIFICAR  (peso 3)  — pior
    ↓
ATENÇÃO    (peso 2)
    ↓
OK         (peso 1)
    ↓
INDISPONÍVEL (peso 0)  — sem dados
```

---

## 🔍 Flags de QA

### Flags Relacionadas a Fontes de Dados

| Flag | Significado | Impacto |
|------|-------------|---------|
| `qa_agua_nsv_usado` | Usado NSV da água em vez de GSV | ⚠️ Menor confiabilidade |
| `qa_water_from_mass_fallback` | Água calculada a partir de massa | ⚠️ Menor precisão |
| `qa_agua_ausente` | Dados de água ausentes | ❌ Bloqueia cálculo |
| `qa_gas_from_mass_fallback` | Gás calculado a partir de massa | ⚠️ Menor precisão |
| `qa_gas_ausente` | Dados de gás ausentes | ❌ Bloqueia cálculo |

### Flags Relacionadas a PVT

| Flag | Significado | Impacto |
|------|-------------|---------|
| `qa_missing_pvt_params` | Parâmetros PVT ausentes/incompletos | ❌ Bloqueia transformações |
| `qa_gsv_unconfirmed` | GSV não confirmado como gross liquid | ❌ Bloqueia cálculo óleo |
| `qa_gsv_ou_agua_ausente` | GSV ou água ausente | ❌ Bloqueia cálculo óleo |
| `qa_gor_fixed_caution` | GOR fixo — comparação gás desabilitada | ⚠️ Trilha standard limitada |
| `qa_gor_mode_unknown` | Modo GOR desconhecido | ❌ Bloqueia trilha standard |

### Flags de Cobertura

| Flag | Significado | Impacto |
|------|-------------|---------|
| `qa_cobertura_incompleta_Xh` | Menos de 24 horas válidas (X horas) | ⚠️ Consolidado parcial |

### Interpretação de Cores (UI)

- 🟢 **OK**: Dentro dos limites esperados
- 🟡 **ATENÇÃO**: Desvio entre 1× e 2× o limite
- 🔴 **VERIFICAR**: Desvio > 2× o limite
- ⚪ **INDISPONÍVEL**: Dados ausentes ou bloqueados

---

## 🔧 Proposta de Fator K

### Conceito

O **fator K** é um multiplicador aplicado às medições do MPFM para ajustá-las à referência do separador:

```
medição_ajustada = medição_mpfm × K
```

### Modos de Proposta

#### 1. **HC** (Hidrocarboneto) — Default
```python
K_proposto = K_atual × (massa_hc_ref_24h / massa_hc_mpfm_24h)
```
Base: Desvio HC 24h

#### 2. **Total** (Massa Total)
```python
K_proposto = K_atual × (massa_total_ref_24h / massa_total_mpfm_24h)
```
Base: Desvio Total 24h

#### 3. **Manual**
```python
K_proposto = valor_digitado_pelo_usuario
```

### Melhoria Esperada

```python
melhoria_pct = |desvio_antes| - |desvio_depois|
```

Onde:
- `desvio_antes` = desvio atual (com K_atual)
- `desvio_depois` = desvio estimado se aplicar K_proposto

### Exemplo Prático

**Situação Atual:**
- K_atual = 1.000
- massa_hc_mpfm = 100 t
- massa_hc_ref = 105 t
- desvio_hc = -4.76%

**Proposta:**
```
K_proposto = 1.000 × (105 / 100) = 1.050
```

**Aplicando K_proposto:**
```
massa_hc_ajustada = 100 × 1.050 = 105 t
desvio_novo = 0%
melhoria = |-4.76%| - |0%| = 4.76 pontos percentuais
```

### Validação da Proposta

A proposta é considerada **válida** se:
1. Existe `K_atual` configurado
2. Existem dados consolidados 24h
3. Status não é 'INDISPONÍVEL'
4. `melhoria_pct > 0` (ou seja, realmente melhora o desvio)

### Limite de Aplicabilidade

A proposta é considerada **dentro do limite** se:
```
|desvio_com_K_proposto| ≤ limite_pct
```

Onde `limite_pct` é:
- `limite_hc_pct` se proposta baseada em HC
- `limite_total_pct` se proposta baseada em Total

---

## 📐 Fórmulas Completas Resumidas

### Óleo Standard
```
oleo_std_reconc_sm3 = (GSV_sep - agua_sep) × FE
```

### Gás Dissolvido
```
gas_dissolvido_sm3 = oleo_std_reconc_sm3 × RS
```

### Gás Total
```
gas_total_sm3 = gas_livre_sep + gas_dissolvido
```

### Massas de Referência
```
massa_oleo_ref_t  = oleo_std_reconc_sm3 × ρ_oleo_std / 1000
massa_gas_ref_t   = gas_total_sm3 × ρ_gas_std / 1000
massa_agua_ref_t  = agua_sep_sm3 × ρ_agua_std / 1000
massa_hc_ref_t    = massa_oleo_ref_t + massa_gas_ref_t
massa_total_ref_t = massa_hc_ref_t + massa_agua_ref_t
```

### Desvios
```
desvio_pct = [(MPFM - REF) / REF] × 100
```

### BSW
```
BSW_calc_pct = (agua_sep_sm3 / GSV_sep_sm3) × 100
```

---

## 🗄️ Estruturas de Dados

### `SepHoraInput`
Dados medidos do **separador** para uma hora:
- `hora`, `dt_str`
- `agua_gsv_sm3`, `agua_nsv_sm3`, `agua_mass_t`
- `gsv_sep_sm3`
- `gas_vol_sm3`, `gas_mass_t`
- `bsw_user_pct`
- `pressao_barg`, `temperatura_c`

### `MPFMHoraInput`
Dados do **MPFM** para uma hora:
- `hora`, `dt_str`
- **Linha corrected**: `oleo_corr_t`, `gas_corr_t`, `agua_corr_t`, `hc_corr_t`, `total_corr_t`
- **Standard @20°C**: `oleo_st_t`, `gas_st_t`, `agua_st_t`, `oleo_st_m3`, `gas_st_ksm3`, `agua_st_m3`
- **Condição linha**: `pressao_barg`, `temperatura_c`, `rho_oleo_linha`, `rho_gas_linha`, `rho_agua_linha`

### `CalcHoraResult`
Resultado completo do cálculo para **uma hora**:
- Cópias das entradas SEP e MPFM
- Trilha PVT (FE, RS, densidades)
- Massas de referência
- Desvios (linha e standard)
- Status (linha, standard, final)
- Flags de QA
- Rastreabilidade de fontes

### `Resumo24h`
Consolidado das **24 horas**:
- Somas linha vs linha
- Somas standard vs standard
- Desvios consolidados
- Status consolidado
- Cobertura temporal (`horas_validas`, `cobertura_pct`)
- Flags consolidadas

---

## 🎓 Glossário

| Termo | Significado |
|-------|-------------|
| **MPFM** | Multiphase Flow Meter — medidor multifásico |
| **SEP** | Separador de teste trifásico (óleo/gás/água) |
| **PVT** | Pressure-Volume-Temperature (análise de fluidos) |
| **FE** | Fator de encolhimento (shrinkage factor) |
| **RS** | Razão de solubilidade (gas/oil ratio dissolved) |
| **GOR** | Gas-Oil Ratio |
| **BSW** | Basic Sediments and Water (água + sedimentos) |
| **GSV** | Gross Standard Volume (volume bruto padrão) |
| **NSV** | Net Standard Volume (volume líquido padrão) |
| **HC** | Hidrocarboneto (óleo + gás) |
| **Sm³** | Standard cubic meter (metro cúbico standard) |
| **kSm³** | Mil metros cúbicos standard (×1000) |
| **Linha** | Condições de linha (pressão/temperatura operação) |
| **Standard** | Condições padrão (20°C, 1 bar) |
| **Corrected** | Dados corrigidos do MPFM (condição linha) |
| **Fator K** | Multiplicador de ajuste das medições do MPFM |

---

## 📚 Arquivos Relacionados

### Motor de Cálculo
- **`recon_engine.py`** — lógica pura de reconciliação
  - Funções: `calcular_hora()`, `calcular_24h()`
  - Estruturas: `SepHoraInput`, `MPFMHoraInput`, `PVTParams`, `CalcHoraResult`, `Resumo24h`

### Persistência
- **`repositories/recon/recon_repository.py`** — CRUD de parâmetros PVT e resultados
  - Tabela SQLite: `pvt_params`

### API
- **`routes/recon_routes.py`** — endpoints de reconciliação
  - POST `/api/recon/calculate-24h` — executa reconciliação
  - GET/POST/PUT/DELETE `/api/recon/pvt-params` — gestão PVT

### Serviços
- **`services/recon.py`** — preparação de dados
  - `build_sep_horas_full()` — constrói `SepHoraInput[]`
  - `build_mpfm_horas()` — constrói `MPFMHoraInput[]`

---

## 📝 Notas Finais

### Pontos de Atenção

1. **GSV Confirmation Critical**
   - Se `gsv_confirmed = False`, toda a trilha standard fica comprometida
   - Sempre validar GSV antes de habilitar reconciliação

2. **GOR Mode Impact**
   - `fixed`/`zero`: comparação de gás bloqueada
   - `unknown`: toda trilha standard bloqueada
   - `triphasic`: modo completo (ideal)

3. **Cobertura Temporal**
   - Consolidado 24h requer pelo menos algumas horas válidas
   - Cobertura < 100% adiciona flag de QA
   - Recomendado: mínimo 20 horas válidas para proposta K confiável

4. **Hierarquia de Fontes**
   - Sistema prioriza dados mais confiáveis
   - Fallbacks (massa → volume) menos precisos
   - Flags de QA registram todas as aproximações

### Melhores Práticas

✅ **Configurar parâmetros PVT atualizados** por campanha/período
✅ **Validar GSV como gross liquid** antes de usar
✅ **Definir limites realistas** (5% HC, 5% Total, 20% Água são padrão)
✅ **Revisar flags de QA** em resultados ATENÇÃO/VERIFICAR
✅ **Propor fator K** apenas com cobertura ≥ 20h
✅ **Documentar fonte** e `valid_from`/`valid_to` em parâmetros PVT

---

**Documento Técnico** — MPFM Manager v4.1  
**Última Atualização**: 28/04/2026  
**Autor**: Documentação gerada a partir do código-fonte da aplicação
