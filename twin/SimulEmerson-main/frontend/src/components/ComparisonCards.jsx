import React from "react";
import { clamp, fmt } from "@/calculations";

export default function ComparisonCards({ r }) {
  const data = [
    { name: "Subsea × Topside", dev: Math.abs(r.deviations.delta_HC) * 0.22 + 1.2, conf: "Alta", color: "var(--green)" },
    { name: "Topside × Separador", dev: Math.abs(r.deviations.delta_HC) * 0.45 + 2.0, conf: "Média", color: "var(--amber)" },
    { name: "Subsea × Separador", dev: Math.abs(r.deviations.delta_HC) * 0.66 + 3.0, conf: "Baixa", color: "var(--red)" },
  ];
  return (
    <div className="comparison-grid" data-testid="comparison-grid">
      {data.map((d) => (
        <div key={d.name} className="comparison-card">
          <strong>{d.name}</strong>
          <div className="comparison-art">▥ ─ ◉ ─ ▧</div>
          <div className="comparison-metric">
            <span>Desvio HC<br /><b style={{ color: d.color }}>{fmt.format(d.dev)}%</b></span>
            <span>Confiança<br /><b>{d.conf}</b></span>
          </div>
          <div className="bar"><i style={{ width: `${clamp(d.dev * 12, 8, 100)}%`, background: d.color }} /></div>
        </div>
      ))}
    </div>
  );
}
