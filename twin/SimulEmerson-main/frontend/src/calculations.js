// Twin MPFM v4 — front-end calculations (port from frontend/app.js)
export const CONSTANTS = {
  T_STD_C: 20,
  P_STD_MPA_ABS: 0.101325,
  P_STD_BARA: 1.01325,
  T_STD_K: 293.15,
  Z_GAS_DEFAULT: 0.90,
  RHO_WATER_PURE_20: 998.2,
  IAJ_TARGET: 60,
  HC_LIMIT_TRIAGE: 5,
  TOTAL_LIMIT_TRIAGE: 7,
  FCS320_MODE: 'external_reference',
  EOS_MODE: 'independent_validation',
  ROUTE_CONFIDENCE_DEFAULT: 'inferred',
  GAS_LIFT_DEFAULT_STATUS: 'not_confirmed',
};

export const fmt = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 });
export const fmt3 = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 });

export const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
export const pct = (v) => `${fmt.format(v * 100)}%`;
export const dec = (v) => fmt.format(v);

export function parseNum(v) {
  if (typeof v === 'number') return Number.isFinite(v) ? v : 0;
  if (!v) return 0;
  return Number(String(v).replace(/\./g, '').replace(',', '.').replace(/[^0-9.+-]/g, '')) || 0;
}

export function classifyEnvelope(gvf, wlr) {
  if (gvf > 0.86 || wlr > 0.78 || (gvf > 0.68 && wlr > 0.52)) return 'Fora do Envelope';
  if (gvf > 0.58 || wlr > 0.45 || (gvf > 0.42 && wlr > 0.34)) return 'Restrita';
  return 'Apta';
}

export function classifyIAJ(iaj, envelopeStatus) {
  if (envelopeStatus === 'Fora do Envelope' || iaj < 55) return 'Bloqueada';
  if (envelopeStatus === 'Restrita' || iaj < 80) return 'Restrita';
  return 'Apta';
}

export function calculateSeparatorBalance(s) {
  const NSV_sep = s.GSV_sep * (1 - s.BSW / 100);
  const V_STO = NSV_sep * s.SF_sep_tank;
  const m_oil_REF = (V_STO * s.rho_oil_STO) / 1000;
  const V_gas_flash_std = V_STO * s.deltaRs_sep_tank;
  const V_gas_total_std = s.V_gas_sep_std + V_gas_flash_std;
  const m_gas_REF = (V_gas_total_std * s.rho_gas_std) / 1000;
  const V_water_oil_std = s.GSV_sep * (s.BSW / 100);
  const V_water_total_std = s.V_water_free_std + V_water_oil_std;
  const m_water_REF = (V_water_total_std * s.rho_water_20) / 1000;
  return {
    NSV_sep, V_STO, m_oil_REF, V_gas_flash_std, V_gas_total_std, m_gas_REF,
    V_water_oil_std, V_water_total_std, m_water_REF,
    m_HC_REF: m_oil_REF + m_gas_REF,
    m_total_REF: m_oil_REF + m_gas_REF + m_water_REF,
  };
}

export function estimateMpfmMasses(i, s) {
  const m_oil_MPFM = (i.qo * s.rho_oil_STO) / 1000;
  const m_gas_MPFM = (Math.max(i.qg - i.gasLift, 0) * s.rho_gas_std) / 1000;
  const m_water_MPFM = (i.qw * s.rho_water_20) / 1000;
  return {
    m_oil_MPFM, m_gas_MPFM, m_water_MPFM,
    m_HC_MPFM: m_oil_MPFM + m_gas_MPFM,
    m_total_MPFM: m_oil_MPFM + m_gas_MPFM + m_water_MPFM,
  };
}

export function calculateDeviations(m, b) {
  const rel = (a, r) => (r ? (100 * (a - r)) / r : 0);
  return {
    delta_oil: rel(m.m_oil_MPFM, b.m_oil_REF),
    delta_gas: rel(m.m_gas_MPFM, b.m_gas_REF),
    delta_water: rel(m.m_water_MPFM, b.m_water_REF),
    delta_HC: rel(m.m_HC_MPFM, b.m_HC_REF),
    delta_total: rel(m.m_total_MPFM, b.m_total_REF),
  };
}

export function normalizedError(xM, xR, uM, uR) {
  return (xM - xR) / Math.sqrt(uM * uM + uR * uR);
}

export function calculateIAJ(x, gasLift) {
  let score = 100;
  if (x.envelopeStatus === 'Restrita') score -= 18;
  if (x.envelopeStatus === 'Fora do Envelope') score -= 42;
  if (x.gvf > 0.65) score -= 12;
  if (x.wlr > 0.50) score -= 10;
  if (Math.abs(x.deviations.delta_HC) > CONSTANTS.HC_LIMIT_TRIAGE) score -= 14;
  if (Math.abs(x.deviations.delta_total) > CONSTANTS.TOTAL_LIMIT_TRIAGE) score -= 14;
  if (gasLift <= 0) score -= 4;
  score -= 5; // rota inferida nesta fase
  return clamp(Math.round(score), 0, 100);
}

export function computeResults(input, separator) {
  const pAbsBara = Math.max(input.pressure + 1.01325, 1.01325);
  const tK = input.temperature + 273.15;
  const qgActual = (input.qg * (CONSTANTS.P_STD_BARA / pAbsBara) * (tK / CONSTANTS.T_STD_K)) / CONSTANTS.Z_GAS_DEFAULT;
  const liquid = Math.max(input.qo + input.qw, 1e-6);
  const gvf = clamp(qgActual / Math.max(qgActual + liquid, 1e-6), 0, 1);
  const wlr = clamp(input.qw / liquid, 0, 1);
  const gor = input.qo > 0 ? input.qg / input.qo : 0;
  const envelopeStatus = classifyEnvelope(gvf, wlr);
  const balance = calculateSeparatorBalance(separator);
  const mpfmMasses = estimateMpfmMasses(input, separator);
  const deviations = calculateDeviations(mpfmMasses, balance);
  const iaj = calculateIAJ({ gvf, wlr, gor, envelopeStatus, deviations }, input.gasLift);
  const technicalStatus = classifyIAJ(iaj, envelopeStatus);
  const factorSuggested = balance.m_HC_REF > 0 && mpfmMasses.m_HC_MPFM > 0
    ? balance.m_HC_REF / mpfmMasses.m_HC_MPFM
    : 1;
  const enHC = normalizedError(mpfmMasses.m_HC_MPFM, balance.m_HC_REF, separator.U_MPFM, separator.U_REF);
  return { qgActual, gvf, wlr, gor, envelopeStatus, balance, mpfmMasses, deviations, iaj, technicalStatus, factorSuggested, enHC };
}

export function buildMemorial(state) {
  const r = state.results, i = state.input, b = r.balance, d = r.deviations;
  return `# Memorial da Janela — Twin MPFM

## Identificação
- Poço / corrente: ${i.well}
- Janela: ${i.windowLabel}
- Par de comparação: ${i.comparisonPair}
- Condição padrão: ${CONSTANTS.T_STD_C} °C e ${CONSTANTS.P_STD_MPA_ABS} MPa abs
- FCS320/PVTPack: referência externa black-box nesta fase
- Rota: inferida
- Gas lift: ${i.gasLift > 0 ? `${fmt3.format(i.gasLift)} Sm³/d descontado` : 'não confirmado; compensação não aplicada'}

## Entradas principais
- P: ${fmt3.format(i.pressure)} barg
- T: ${fmt3.format(i.temperature)} °C
- Qo: ${fmt3.format(i.qo)} m³/d
- Qw: ${fmt3.format(i.qw)} m³/d
- Qg: ${fmt3.format(i.qg)} Sm³/d

## Consultor de Aplicabilidade
- GVF: ${fmt3.format(r.gvf)}
- WLR: ${fmt3.format(r.wlr)}
- GOR: ${fmt3.format(r.gor)} Sm³/Sm³
- Envelope: ${r.envelopeStatus}
- IAJ: ${r.iaj}
- Status: ${r.technicalStatus}
- Fator sugerido: ${fmt3.format(r.factorSuggested)} — requer aprovação

## Balanço Separador / Referência
- NSV_sep: ${fmt3.format(b.NSV_sep)} m³ @20°C
- V_STO: ${fmt3.format(b.V_STO)} Sm³ @20°C
- m_oil_REF: ${fmt3.format(b.m_oil_REF)} t
- V_gas_flash_std: ${fmt3.format(b.V_gas_flash_std)} Sm³
- V_gas_total_std: ${fmt3.format(b.V_gas_total_std)} Sm³
- m_gas_REF: ${fmt3.format(b.m_gas_REF)} t
- V_water_total_std: ${fmt3.format(b.V_water_total_std)} m³ @20°C
- m_water_REF: ${fmt3.format(b.m_water_REF)} t
- m_HC_REF: ${fmt3.format(b.m_HC_REF)} t
- m_total_REF: ${fmt3.format(b.m_total_REF)} t

## Desvios relativos
- δ_oil: ${fmt3.format(d.delta_oil)} %
- δ_gas: ${fmt3.format(d.delta_gas)} %
- δ_water: ${fmt3.format(d.delta_water)} %
- δ_HC: ${fmt3.format(d.delta_HC)} %
- δ_total: ${fmt3.format(d.delta_total)} %
- En_HC: ${fmt3.format(r.enHC)}

## Observações técnicas
- SF_sep→tank não é tratado como 1/Bo genérico sem equivalência demonstrada.
- ΔRs_sep→tank é tratado como gás incremental liberado no caminho separador→tanque, não como Rs total de reservatório.
- Densidade Coriolis, quando disponível, deve ser usada para diagnóstico de coerência e não automaticamente como ρ_oil_STO.
- Critérios fixos de triagem não são declarados como tolerância normativa universal; compatibilidade por En deve prevalecer quando houver incertezas.
`;
}

export function downloadFile(filename, content, type = 'text/plain;charset=utf-8') {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 500);
}
