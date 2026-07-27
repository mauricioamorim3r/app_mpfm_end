import React, { useMemo } from "react";
import { calculateSeparatorBalance, fmt3, parseNum } from "@/calculations";

const FIELDS = [
  ["GSV_sep", "GSV sep (m³ @20°C)"],
  ["BSW", "BSW (%)"],
  ["SF_sep_tank", "SF sep→tank"],
  ["rho_oil_STO", "ρ óleo STO (kg/m³)"],
  ["V_gas_sep_std", "V gás sep std (Sm³)"],
  ["deltaRs_sep_tank", "ΔRs sep→tank"],
  ["rho_gas_std", "ρ gás std (kg/Sm³)"],
  ["V_water_free_std", "V água livre (m³)"],
  ["rho_water_20", "ρ água 20°C (kg/m³)"],
  ["U_MPFM", "U MPFM (%)"],
  ["U_REF", "U REF (%)"],
];

export default function BalanceView({ separator, setSeparator }) {
  const b = useMemo(() => calculateSeparatorBalance(separator), [separator]);
  const upd = (k, v) => setSeparator((s) => ({ ...s, [k]: parseNum(v) }));
  return (
    <section data-testid="balance-view" className="active-view">
      <section className="panel section-header">
        <h2>Balanço Separador / Referência</h2>
        <p>Motor operacional para transformar medições do separador de teste em referência por fase: óleo estabilizado, gás associado e água produzida.</p>
      </section>
      <section className="balance-layout">
        <article className="panel form-panel">
          <h3>Entradas do Separador</h3>
          <div className="two-col-form" data-testid="separator-form">
            {FIELDS.map(([k, l]) => (
              <div key={k} className="field">
                <label>{l}</label>
                <input
                  data-testid={`sep-${k}`}
                  defaultValue={String(separator[k]).replace(".", ",")}
                  onBlur={(e) => upd(k, e.target.value)}
                  inputMode="decimal"
                />
              </div>
            ))}
          </div>
          <button type="button" className="primary-button" data-testid="run-balance">Calcular Balanço</button>
        </article>
        <article className="panel">
          <div className="panel-head">
            <h3>Resultados calculados</h3>
            <span>Condição padrão: 20 °C / 0,101325 MPa abs</span>
          </div>
          <div className="result-grid" data-testid="balance-results">
            {Object.entries(b).map(([k, v]) => (
              <div key={k} className="result-card">
                <span>{k}</span>
                <strong>{fmt3.format(v)}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>
      <article className="panel" style={{ padding: 16 }}>
        <h3>Memorial matemático aplicado</h3>
        <pre className="formula-block" data-testid="balance-formula">
{`NSV_sep = GSV_sep × (1 - BSW/100) = ${fmt3.format(b.NSV_sep)} m³
V_STO = NSV_sep × SF_sep→tank = ${fmt3.format(b.V_STO)} Sm³
m_oil_REF = V_STO × ρ_oil_STO / 1000 = ${fmt3.format(b.m_oil_REF)} t
V_gas_flash_std = V_STO × ΔRs_sep→tank = ${fmt3.format(b.V_gas_flash_std)} Sm³
V_gas_total_std = V_gas_sep_std + V_gas_flash_std = ${fmt3.format(b.V_gas_total_std)} Sm³
m_gas_REF = V_gas_total_std × ρ_gas_std / 1000 = ${fmt3.format(b.m_gas_REF)} t
V_water_total_std = V_water_free_std + GSV_sep × BSW/100 = ${fmt3.format(b.V_water_total_std)} m³
m_water_REF = V_water_total_std × ρ_water_20 / 1000 = ${fmt3.format(b.m_water_REF)} t
m_HC_REF = m_oil_REF + m_gas_REF = ${fmt3.format(b.m_HC_REF)} t
m_total_REF = m_HC_REF + m_water_REF = ${fmt3.format(b.m_total_REF)} t`}
        </pre>
      </article>
    </section>
  );
}
