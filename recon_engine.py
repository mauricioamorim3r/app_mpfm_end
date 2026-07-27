#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recon_engine.py — Reconciliação externa SEP × MPFM
===================================================
Motor de cálculo PURO (sem dependências de banco de dados).
Transforma dados medidos do separador de teste, com apoio de parâmetros
PVT externos, em grandezas equivalentes comparáveis às do MPFM.

Metodologia: PE-02 Memorial Ajustado + Anexo de Implementação Ajustado
Referência: 20 °C / 1,01325 bar(a)

Não reproduz o cálculo interno do FCS320/MPFM.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


# ─────────────────────────────────────────────────────────────────────────────
# Estruturas de dados
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PVTParams:
    """Parâmetros PVT versionados por banco/poço/TAG."""
    bank:               str
    tag:                str
    fe:                 float           # Fator de encolhimento (adimensional)
    rs:                 float           # Razão de solubilidade (Sm³/Sm³)
    rho_oleo_std:       float           # Densidade óleo standard (kg/m³)
    rho_gas_std:        float           # Densidade gás standard (kg/m³)
    rho_agua_std:       float           # Densidade água standard (kg/m³)
    temp_ref_c:         float = 20.0    # Temperatura de referência (°C)
    pres_ref_bar:       float = 1.01325 # Pressão de referência (bar a)
    gsv_confirmed:      bool  = False   # GSV do óleo confirmado como gross liquid volume
    gor_mode:           str   = 'unknown'  # fixed | zero | triphasic | unknown
    limite_hc_pct:      float = 5.0     # Limite de alerta HC (%)
    limite_total_pct:   float = 5.0     # Limite de alerta Total (%)
    limite_agua_pct:    float = 20.0    # Limite de alerta Água (%)
    source:             str   = ''
    author:             str   = ''
    notes:              str   = ''
    valid_from:         str   = ''
    valid_to:           str   = ''


@dataclass
class SepHoraInput:
    """Dados medidos do separador para uma hora."""
    hora:           int
    dt_str:         str   = ''
    # Água — prioridade: GSV > NSV > mass
    agua_gsv_sm3:   Optional[float] = None   # GSV do TXT de água (PRIORIDADE 1)
    agua_nsv_sm3:   Optional[float] = None   # NSV do TXT de água (aceito se BSW=0)
    agua_mass_t:    Optional[float] = None   # Massa de água (fallback)
    # Óleo/líquido — só usar subtração se gsv_confirmed=True
    gsv_sep_sm3:    Optional[float] = None   # GSV do TXT de óleo (gross liquid)
    # Gás livre — prioridade: volume standard > reconstruído por massa
    gas_vol_sm3:    Optional[float] = None   # Volume standard do gás (PRIORIDADE 1)
    gas_mass_t:     Optional[float] = None   # Massa de gás (fallback para vol)
    # QA
    bsw_user_pct:   Optional[float] = None   # BSW informado pelo usuário (%)
    pressao_barg:   Optional[float] = None
    temperatura_c:  Optional[float] = None


@dataclass
class MPFMHoraInput:
    """Dados do MPFM para uma hora (base linha e standard)."""
    hora:               int
    dt_str:             str   = ''
    # Linha — corrected
    oleo_corr_t:        Optional[float] = None
    gas_corr_t:         Optional[float] = None
    agua_corr_t:        Optional[float] = None
    hc_corr_t:          Optional[float] = None
    total_corr_t:       Optional[float] = None
    # Standard @20°C
    oleo_st_t:          Optional[float] = None
    gas_st_t:           Optional[float] = None
    agua_st_t:          Optional[float] = None
    oleo_st_m3:         Optional[float] = None
    gas_st_ksm3:        Optional[float] = None   # kSm³
    agua_st_m3:         Optional[float] = None
    # Condição de linha
    pressao_barg:       Optional[float] = None
    temperatura_c:      Optional[float] = None
    rho_oleo_linha:     Optional[float] = None   # kg/m³ — linha, NÃO standard
    rho_gas_linha:      Optional[float] = None
    rho_agua_linha:     Optional[float] = None


@dataclass
class CalcHoraResult:
    """Resultado completo do cálculo para uma hora — espelha Calculo_Ref_Hora."""
    hora:                   int
    dt_str:                 str   = ''

    # ── Entradas do separador (copiadas/roteadas) ──────────────────────────
    gsv_sep_sm3:            Optional[float] = None
    agua_sep_sm3:           Optional[float] = None   # campo efetivamente usado
    gas_livre_sep_sm3:      Optional[float] = None   # campo efetivamente usado
    bsw_user_pct:           Optional[float] = None
    bsw_calc_pct:           Optional[float] = None

    # ── Trilha PVT ─────────────────────────────────────────────────────────
    oleo_base_ref_sm3:      Optional[float] = None
    fe:                     Optional[float] = None
    rs:                     Optional[float] = None
    oleo_std_reconc_sm3:    Optional[float] = None
    gas_dissolvido_sm3:     Optional[float] = None
    gas_total_reconc_sm3:   Optional[float] = None
    rho_oleo_std:           Optional[float] = None
    rho_gas_std:            Optional[float] = None
    rho_agua_std:           Optional[float] = None

    # ── Massas de referência (t) ────────────────────────────────────────────
    massa_oleo_ref_t:       Optional[float] = None
    massa_gas_ref_t:        Optional[float] = None
    massa_agua_ref_t:       Optional[float] = None
    massa_hc_ref_t:         Optional[float] = None
    massa_total_ref_t:      Optional[float] = None

    # ── KPIs ──────────────────────────────────────────────────────────────
    desvio_hc_linha_pct:    Optional[float] = None
    desvio_total_linha_pct: Optional[float] = None
    desvio_agua_linha_pct:  Optional[float] = None
    desvio_oleo_st_pct:     Optional[float] = None   # trilha standard
    desvio_gas_st_pct:      Optional[float] = None   # trilha standard

    # ── QA ────────────────────────────────────────────────────────────────
    qa_gap_bsw_pp:          Optional[float] = None
    flag_bsw:               str = ''
    status_linha:           str = ''
    status_standard:        str = ''
    status_final:           str = ''

    # ── Flags de rastreabilidade ──────────────────────────────────────────
    agua_fonte:             str = ''   # 'gsv' | 'nsv' | 'mass_fallback' | 'blocked'
    gas_fonte:              str = ''   # 'vol_direto' | 'mass_fallback' | 'blocked'
    pvt_bloqueado:          bool = False
    gsv_oleo_bloqueado:     bool = False
    gor_fixed_caution:      bool = False
    qa_flags:               List[str] = field(default_factory=list)

    hora_valida:            bool = True   # False se dados críticos ausentes


@dataclass
class Resumo24h:
    """Consolidado das 24 horas — espelha Resumo_24h."""
    # Linha vs linha
    massa_hc_ref_t:         Optional[float] = None
    massa_hc_mpfm_t:        Optional[float] = None
    desvio_hc_pct:          Optional[float] = None
    status_hc:              str = ''

    massa_total_ref_t:      Optional[float] = None
    massa_total_mpfm_t:     Optional[float] = None
    desvio_total_pct:       Optional[float] = None
    status_total:           str = ''

    massa_agua_ref_t:       Optional[float] = None
    massa_agua_mpfm_t:      Optional[float] = None
    desvio_agua_pct:        Optional[float] = None
    status_agua:            str = ''

    status_linha:           str = ''

    # Standard vs standard
    oleo_std_ref_sm3:       Optional[float] = None
    oleo_st_mpfm_m3:        Optional[float] = None
    desvio_oleo_st_pct:     Optional[float] = None
    status_oleo_st:         str = ''

    gas_total_ref_sm3:      Optional[float] = None
    gas_st_mpfm_ksm3:       Optional[float] = None
    desvio_gas_st_pct:      Optional[float] = None
    status_gas_st:          str = ''

    agua_ref_sm3:           Optional[float] = None
    agua_st_mpfm_m3:        Optional[float] = None
    desvio_agua_st_pct:     Optional[float] = None
    status_agua_st:         str = ''

    status_standard:        str = ''

    # Cobertura e QA
    horas_validas:          int = 0
    horas_janela:           int = 24   # tamanho da janela de teste (24h por padrão)
    cobertura_pct:          float = 0.0
    consolidado_completo:   bool = False
    qa_gap_bsw_medio_pp:    Optional[float] = None
    flag_bsw_consolidado:   str = ''
    flag_gsv_nao_confirmado: bool = False
    flag_gor_fixed_caution: bool = False
    qa_flags_consolidados:  List[str] = field(default_factory=list)

    status_final:           str = ''


# ─────────────────────────────────────────────────────────────────────────────
# Funções auxiliares
# ─────────────────────────────────────────────────────────────────────────────

def _nan(v) -> bool:
    """True se valor é None ou NaN."""
    if v is None: return True
    try: return math.isnan(float(v))
    except (TypeError, ValueError): return True


def _f(v, default=None) -> Optional[float]:
    """Converte para float seguro."""
    if _nan(v): return default
    try: return float(v)
    except (TypeError, ValueError): return default


def _desvio_pct(mpfm: Optional[float], ref: Optional[float]) -> Optional[float]:
    """Desvio percentual: (MPFM - REF) / REF × 100. None se dados ausentes ou REF=0."""
    if _nan(mpfm) or _nan(ref) or ref == 0: return None
    return round((mpfm / ref - 1.0) * 100.0, 6)


def _status(desvio: Optional[float], limite: float) -> str:
    """Retorna OK / ATENÇÃO / VERIFICAR / INDISPONÍVEL."""
    if _nan(desvio): return 'INDISPONÍVEL'
    a = abs(desvio)
    if a <= limite: return 'OK'
    if a <= limite * 2: return 'ATENÇÃO'
    return 'VERIFICAR'


def _bsw_calc(agua_sm3: Optional[float], gsv_sm3: Optional[float]) -> Optional[float]:
    """BSW calculado = água / GSV × 100 (%)."""
    if _nan(agua_sm3) or _nan(gsv_sm3) or gsv_sm3 == 0: return None
    return round(agua_sm3 / gsv_sm3 * 100.0, 6)


def _soma_valida(valores: List[Optional[float]]) -> Optional[float]:
    """Soma ignorando None. Retorna None se todos forem None."""
    validos = [v for v in valores if not _nan(v)]
    return round(sum(validos), 6) if validos else None


# ─────────────────────────────────────────────────────────────────────────────
# Engine hora a hora
# ─────────────────────────────────────────────────────────────────────────────

def calcular_hora(
    sep: SepHoraInput,
    mpfm: MPFMHoraInput,
    pvt: PVTParams,
) -> CalcHoraResult:
    """
    Executa o cálculo de reconciliação para uma hora.
    Retorna CalcHoraResult com todos os campos preenchidos ou None/flags de bloqueio.
    """
    r = CalcHoraResult(hora=sep.hora, dt_str=sep.dt_str)
    r.fe  = pvt.fe
    r.rs  = pvt.rs
    r.rho_oleo_std = pvt.rho_oleo_std
    r.rho_gas_std  = pvt.rho_gas_std
    r.rho_agua_std = pvt.rho_agua_std

    # ── 1. Água do separador — hierarquia obrigatória ─────────────────────
    if not _nan(sep.agua_gsv_sm3):
        r.agua_sep_sm3 = _f(sep.agua_gsv_sm3)
        r.agua_fonte   = 'gsv'
    elif not _nan(sep.agua_nsv_sm3):
        r.agua_sep_sm3 = _f(sep.agua_nsv_sm3)
        r.agua_fonte   = 'nsv'
        r.qa_flags.append('qa_agua_nsv_usado')
    elif not _nan(sep.agua_mass_t) and not _nan(pvt.rho_agua_std) and pvt.rho_agua_std > 0:
        # Fallback: massa → volume usando ρ standard
        r.agua_sep_sm3 = round(_f(sep.agua_mass_t) * 1000.0 / pvt.rho_agua_std, 6)
        r.agua_fonte   = 'mass_fallback'
        r.qa_flags.append('qa_water_from_mass_fallback')
    else:
        r.agua_sep_sm3 = None
        r.agua_fonte   = 'blocked'
        r.qa_flags.append('qa_agua_ausente')

    # ── 2. Gás livre do separador ─────────────────────────────────────────
    if not _nan(sep.gas_vol_sm3):
        r.gas_livre_sep_sm3 = _f(sep.gas_vol_sm3)
        r.gas_fonte         = 'vol_direto'
    elif not _nan(sep.gas_mass_t) and not _nan(pvt.rho_gas_std) and pvt.rho_gas_std > 0:
        # Fallback: massa → volume standard
        r.gas_livre_sep_sm3 = round(_f(sep.gas_mass_t) * 1000.0 / pvt.rho_gas_std, 6)
        r.gas_fonte         = 'mass_fallback'
        r.qa_flags.append('qa_gas_from_mass_fallback')
    else:
        r.gas_livre_sep_sm3 = None
        r.gas_fonte         = 'blocked'
        r.qa_flags.append('qa_gas_ausente')

    # ── 3. GSV do óleo — só usar subtração se gsv_confirmed ──────────────
    r.gsv_sep_sm3 = _f(sep.gsv_sep_sm3)
    if not pvt.gsv_confirmed:
        r.oleo_base_ref_sm3  = None
        r.gsv_oleo_bloqueado = True
        r.qa_flags.append('qa_gsv_unconfirmed')
    elif _nan(r.gsv_sep_sm3) or _nan(r.agua_sep_sm3):
        r.oleo_base_ref_sm3  = None
        r.gsv_oleo_bloqueado = True
        r.qa_flags.append('qa_gsv_ou_agua_ausente')
    else:
        r.oleo_base_ref_sm3 = round(r.gsv_sep_sm3 - r.agua_sep_sm3, 6)

    # ── 4. BSW calculado e QA ─────────────────────────────────────────────
    r.bsw_user_pct = _f(sep.bsw_user_pct)
    r.bsw_calc_pct = _bsw_calc(r.agua_sep_sm3, r.gsv_sep_sm3)
    if not _nan(r.bsw_user_pct) and not _nan(r.bsw_calc_pct):
        r.qa_gap_bsw_pp = round(abs(r.bsw_user_pct - r.bsw_calc_pct), 4)
        r.flag_bsw = 'OK' if r.qa_gap_bsw_pp <= 0.5 else 'ATENÇÃO'
    else:
        r.qa_gap_bsw_pp = None
        r.flag_bsw = 'INDISPONÍVEL'

    # ── 5. Trilha PVT ────────────────────────────────────────────────────
    pvt_ok = (not _nan(pvt.fe) and not _nan(pvt.rs)
              and not _nan(pvt.rho_oleo_std) and not _nan(pvt.rho_gas_std)
              and not _nan(pvt.rho_agua_std))
    if not pvt_ok:
        r.pvt_bloqueado = True
        r.qa_flags.append('qa_missing_pvt_params')
    
    if pvt_ok and not _nan(r.oleo_base_ref_sm3):
        r.oleo_std_reconc_sm3  = round(_f(r.oleo_base_ref_sm3) * pvt.fe, 6)
        r.gas_dissolvido_sm3   = round(r.oleo_std_reconc_sm3 * pvt.rs, 6)
    else:
        r.oleo_std_reconc_sm3 = None
        r.gas_dissolvido_sm3  = None

    if not _nan(r.gas_livre_sep_sm3) and not _nan(r.gas_dissolvido_sm3):
        r.gas_total_reconc_sm3 = round(r.gas_livre_sep_sm3 + r.gas_dissolvido_sm3, 6)
    elif not _nan(r.gas_livre_sep_sm3):
        # Sem gás dissolvido (sem PVT), usar apenas gás livre
        r.gas_total_reconc_sm3 = r.gas_livre_sep_sm3
    else:
        r.gas_total_reconc_sm3 = None

    # ── 6. Massas de referência (t) ───────────────────────────────────────
    if pvt_ok:
        if not _nan(r.oleo_std_reconc_sm3):
            r.massa_oleo_ref_t = round(r.oleo_std_reconc_sm3 * pvt.rho_oleo_std / 1000.0, 6)
        if not _nan(r.gas_total_reconc_sm3):
            r.massa_gas_ref_t = round(r.gas_total_reconc_sm3 * pvt.rho_gas_std / 1000.0, 6)
        if not _nan(r.agua_sep_sm3):
            r.massa_agua_ref_t = round(r.agua_sep_sm3 * pvt.rho_agua_std / 1000.0, 6)

    r.massa_hc_ref_t    = _soma_valida([r.massa_oleo_ref_t, r.massa_gas_ref_t])
    r.massa_total_ref_t = _soma_valida([r.massa_hc_ref_t, r.massa_agua_ref_t])

    # ── 7. KPIs linha vs linha ────────────────────────────────────────────
    r.desvio_hc_linha_pct    = _desvio_pct(_f(mpfm.hc_corr_t),    r.massa_hc_ref_t)
    r.desvio_total_linha_pct = _desvio_pct(_f(mpfm.total_corr_t),  r.massa_total_ref_t)
    r.desvio_agua_linha_pct  = _desvio_pct(_f(mpfm.agua_corr_t),   r.massa_agua_ref_t)

    # ── 8. KPIs standard vs standard ─────────────────────────────────────
    gor_fixed = pvt.gor_mode in ('fixed', 'zero')
    r.gor_fixed_caution = gor_fixed
    if gor_fixed:
        r.qa_flags.append('qa_gor_fixed_caution')
        r.desvio_oleo_st_pct = _desvio_pct(_f(mpfm.oleo_st_m3), r.oleo_std_reconc_sm3)
        r.desvio_gas_st_pct  = None  # bloqueado
    elif pvt.gor_mode == 'unknown':
        r.qa_flags.append('qa_gor_mode_unknown')
        r.desvio_oleo_st_pct = None
        r.desvio_gas_st_pct  = None
    else:
        r.desvio_oleo_st_pct = _desvio_pct(_f(mpfm.oleo_st_m3), r.oleo_std_reconc_sm3)
        gas_mpfm_sm3 = (_f(mpfm.gas_st_ksm3) * 1000.0) if not _nan(mpfm.gas_st_ksm3) else None
        r.desvio_gas_st_pct  = _desvio_pct(gas_mpfm_sm3, r.gas_total_reconc_sm3)

    # ── 9. Status hora ────────────────────────────────────────────────────
    r.status_linha = _status(r.desvio_hc_linha_pct, pvt.limite_hc_pct)
    if r.status_linha == 'OK':
        r.status_linha = _status(r.desvio_total_linha_pct, pvt.limite_total_pct)

    st_oleo_st = _status(r.desvio_oleo_st_pct, pvt.limite_hc_pct)
    st_gas_st  = _status(r.desvio_gas_st_pct,  pvt.limite_total_pct)
    rank = {'VERIFICAR': 3, 'ATENÇÃO': 2, 'OK': 1, 'INDISPONÍVEL': 0}
    r.status_standard = max([st_oleo_st, st_gas_st],
                             key=lambda s: rank.get(s, 0))
    r.status_final = max([r.status_linha, r.status_standard],
                          key=lambda s: rank.get(s, 0))

    # Hora válida se tiver pelo menos água + MPFM HC
    r.hora_valida = (not _nan(r.agua_sep_sm3) and not _nan(mpfm.hc_corr_t))

    return r


# ─────────────────────────────────────────────────────────────────────────────
# Consolidado 24h
# ─────────────────────────────────────────────────────────────────────────────

def calcular_24h(
    resultados: List[CalcHoraResult],
    mpfm_horas: List[MPFMHoraInput],
    pvt: PVTParams,
    test_window_horas: Optional[List[int]] = None,
) -> Resumo24h:
    """Consolida as horas válidas em resumo de 24h.

    Args:
        resultados: lista de CalcHoraResult (todas as horas calculadas).
        mpfm_horas: lista de MPFMHoraInput para buscar somas MPFM.
        pvt: parâmetros PVT (limites, gor_mode, etc.).
        test_window_horas: lista de horas inteiras que compõem a janela de
            teste (ex: [6,7,8,9,10,11,12,13] para um teste de 6h às 14h).
            Se None, usa janela de 24h completa (comportamento padrão).
            A cobertura é calculada em relação ao tamanho da janela.
            consolidado_completo = True quando todas as horas da janela
            têm dados válidos.
    """
    res = Resumo24h()

    # Determinar quais resultados pertencem à janela de interesse
    if test_window_horas is not None:
        janela = set(int(h) for h in test_window_horas)
        candidatos = [r for r in resultados if r.hora in janela]
        tamanho_janela = len(janela)
    else:
        candidatos = list(resultados)
        tamanho_janela = 24

    res.horas_janela = tamanho_janela  # novo campo

    validos = [r for r in candidatos if r.hora_valida]
    res.horas_validas = len(validos)
    res.cobertura_pct = round(len(validos) / max(tamanho_janela, 1) * 100.0, 1)
    res.consolidado_completo = (len(validos) == tamanho_janela)

    if not validos:
        res.status_final = 'INDISPONÍVEL'
        return res

    # Somas das referências
    res.massa_hc_ref_t    = _soma_valida([r.massa_hc_ref_t    for r in validos])
    res.massa_total_ref_t = _soma_valida([r.massa_total_ref_t for r in validos])
    res.massa_agua_ref_t  = _soma_valida([r.massa_agua_ref_t  for r in validos])
    res.oleo_std_ref_sm3  = _soma_valida([r.oleo_std_reconc_sm3  for r in validos])
    res.gas_total_ref_sm3 = _soma_valida([r.gas_total_reconc_sm3 for r in validos])
    res.agua_ref_sm3      = _soma_valida([r.agua_sep_sm3 for r in validos])

    # Somas do MPFM
    mpfm_map = {m.hora: m for m in mpfm_horas}
    horas_v  = {r.hora for r in validos}
    mpfm_v   = [mpfm_map[h] for h in horas_v if h in mpfm_map]

    res.massa_hc_mpfm_t    = _soma_valida([_f(m.hc_corr_t)    for m in mpfm_v])
    res.massa_total_mpfm_t = _soma_valida([_f(m.total_corr_t) for m in mpfm_v])
    res.massa_agua_mpfm_t  = _soma_valida([_f(m.agua_corr_t)  for m in mpfm_v])
    res.oleo_st_mpfm_m3    = _soma_valida([_f(m.oleo_st_m3)   for m in mpfm_v])
    res.gas_st_mpfm_ksm3   = _soma_valida([_f(m.gas_st_ksm3)  for m in mpfm_v])
    res.agua_st_mpfm_m3    = _soma_valida([_f(m.agua_st_m3)   for m in mpfm_v])

    # Desvios consolidados
    res.desvio_hc_pct    = _desvio_pct(res.massa_hc_mpfm_t,    res.massa_hc_ref_t)
    res.desvio_total_pct = _desvio_pct(res.massa_total_mpfm_t,  res.massa_total_ref_t)
    res.desvio_agua_pct  = _desvio_pct(res.massa_agua_mpfm_t,   res.massa_agua_ref_t)
    res.desvio_oleo_st_pct = _desvio_pct(res.oleo_st_mpfm_m3,  res.oleo_std_ref_sm3)

    gas_st_mpfm_sm3 = (res.gas_st_mpfm_ksm3 * 1000.0
                       if not _nan(res.gas_st_mpfm_ksm3) else None)
    gor_fixed = pvt.gor_mode in ('fixed', 'zero')
    res.desvio_gas_st_pct = (None if gor_fixed
                              else _desvio_pct(gas_st_mpfm_sm3, res.gas_total_ref_sm3))
    res.desvio_agua_st_pct = _desvio_pct(res.agua_st_mpfm_m3, res.agua_ref_sm3)

    # Status
    res.status_hc    = _status(res.desvio_hc_pct,    pvt.limite_hc_pct)
    res.status_total = _status(res.desvio_total_pct,  pvt.limite_total_pct)
    res.status_agua  = _status(res.desvio_agua_pct,   pvt.limite_agua_pct)

    rank = {'VERIFICAR': 3, 'ATENÇÃO': 2, 'OK': 1, 'INDISPONÍVEL': 0}
    res.status_linha = max([res.status_hc, res.status_total],
                            key=lambda s: rank.get(s, 0))

    res.status_oleo_st = _status(res.desvio_oleo_st_pct, pvt.limite_hc_pct)
    res.status_gas_st  = _status(res.desvio_gas_st_pct,  pvt.limite_total_pct)
    res.status_agua_st = _status(res.desvio_agua_st_pct, pvt.limite_agua_pct)
    res.status_standard = max([res.status_oleo_st, res.status_gas_st],
                               key=lambda s: rank.get(s, 0))

    res.status_final = max([res.status_linha, res.status_standard],
                            key=lambda s: rank.get(s, 0))

    # QA consolidado
    gaps = [r.qa_gap_bsw_pp for r in validos if not _nan(r.qa_gap_bsw_pp)]
    res.qa_gap_bsw_medio_pp = round(sum(gaps)/len(gaps), 4) if gaps else None
    res.flag_bsw_consolidado = ('OK' if (not _nan(res.qa_gap_bsw_medio_pp)
                                          and res.qa_gap_bsw_medio_pp <= 0.5)
                                 else 'ATENÇÃO' if not _nan(res.qa_gap_bsw_medio_pp)
                                 else 'INDISPONÍVEL')

    all_flags = []
    for r in resultados:
        all_flags.extend(r.qa_flags)
    res.qa_flags_consolidados = sorted(set(all_flags))
    res.flag_gsv_nao_confirmado = 'qa_gsv_unconfirmed' in res.qa_flags_consolidados
    res.flag_gor_fixed_caution  = 'qa_gor_fixed_caution' in res.qa_flags_consolidados

    if not res.consolidado_completo:
        faltando = tamanho_janela - res.horas_validas
        res.qa_flags_consolidados.append(
            f'qa_cobertura_incompleta_{res.horas_validas}h_de_{tamanho_janela}h')

    return res


# ─────────────────────────────────────────────────────────────────────────────
# Exportação para dicionário (para JSON/banco)
# ─────────────────────────────────────────────────────────────────────────────

def hora_to_dict(r: CalcHoraResult) -> Dict[str, Any]:
    d = asdict(r)
    # qa_flags → string separada por '|'
    d['qa_flags'] = '|'.join(r.qa_flags)
    return d


def resumo_to_dict(r: Resumo24h) -> Dict[str, Any]:
    d = asdict(r)
    d['qa_flags_consolidados'] = '|'.join(r.qa_flags_consolidados)
    return d
