import React, { useState } from "react";

const FORM_FIELDS = [
  ["fluidId", "Fluido (ex: PE-4 / PW-104)", "text", true],
  ["source", "Fonte (SLB, PVTSim, ...)", "text", false],
  ["eos", "EOS", "text", false],
  ["status", "Status", "text", false],
  ["SF_sep_tank", "SF_sep→tank", "number", false],
  ["deltaRs_sep_tank", "ΔRs_sep→tank", "number", false],
  ["rho_oil_STO", "ρ óleo STO (kg/m³)", "number", false],
  ["rho_gas_std", "ρ gás std (kg/Sm³)", "number", false],
];

const EMPTY_FORM = {
  fluidId: "", source: "SLB", eos: "SRK + Peneloux",
  SF_sep_tank: "", deltaRs_sep_tank: "", rho_oil_STO: "", rho_gas_std: "",
  status: "validated_tabulated",
};

export default function PVTModal({ onSave, onClose }) {
  const [form, setForm] = useState(EMPTY_FORM);

  const submit = async (e) => {
    e.preventDefault();
    const payload = { ...form };
    ["SF_sep_tank", "deltaRs_sep_tank", "rho_oil_STO", "rho_gas_std"].forEach((k) => {
      payload[k] = payload[k] === "" ? null : Number(payload[k]);
    });
    await onSave(payload);
    setForm(EMPTY_FORM);
  };

  return (
    <dialog open className="report-dialog" data-testid="pvt-modal">
      <form onSubmit={submit} style={{ padding: 18 }}>
        <div className="panel-head">
          <h2>Nova amostra PVT</h2>
          <button type="button" className="icon-button" onClick={onClose}>×</button>
        </div>
        <div className="pvt-form-grid">
          {FORM_FIELDS.map(([k, l, t, req]) => (
            <div key={k} className="field">
              <label>{l}</label>
              <input
                data-testid={`pvt-form-${k}`}
                type={t} step="any" required={req}
                value={form[k]} onChange={(e) => setForm((f) => ({ ...f, [k]: e.target.value }))}
              />
            </div>
          ))}
        </div>
        <div className="dialog-actions">
          <button type="button" className="ghost-button" onClick={onClose}>Cancelar</button>
          <button type="submit" className="primary-button" data-testid="pvt-save">Salvar amostra</button>
        </div>
      </form>
    </dialog>
  );
}
