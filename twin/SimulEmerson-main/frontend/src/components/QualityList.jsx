import React from "react";
import { dec } from "@/calculations";

export default function QualityList({ input, pvt }) {
  const rows = [
    ["Pressão", input.pressure > 0, `${dec(input.pressure)} barg`],
    ["Temperatura", input.temperature > 0, `${dec(input.temperature)} °C`],
    ["Vazão de Óleo (Qo)", input.qo > 0, `${dec(input.qo)} m³/d`],
    ["Vazão de Água (Qw)", input.qw >= 0, `${dec(input.qw)} m³/d`],
    ["Vazão de Gás (Qg)", input.qg >= 0, `${dec(input.qg)} Sm³/d`],
    ["Gas Lift", input.gasLift > 0, input.gasLift > 0 ? `${dec(input.gasLift)} Sm³/d` : "Não confirmado"],
    ["PVT incremental", pvt.deltaRs_sep_tank > 0, `ΔRs ${dec(pvt.deltaRs_sep_tank)}`],
    ["Roteamento", false, "Inferido"],
  ];
  return (
    <div className="quality-list" data-testid="quality-list">
      {rows.map(([name, ok, value]) => (
        <div key={name} className="quality-item">
          <span className={`status-dot ${ok ? "ok" : "warn"}`}>{ok ? "✓" : "!"}</span>
          <strong>{name}</strong>
          <span>{value}</span>
        </div>
      ))}
    </div>
  );
}
