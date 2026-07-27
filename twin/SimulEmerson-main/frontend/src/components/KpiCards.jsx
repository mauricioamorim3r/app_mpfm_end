import React from "react";
import { dec, fmt3, pct } from "@/calculations";

// Configuração estática dos 6 KPIs — uma fonte única da verdade.
// Mapa status → cor (substitui ternário encadeado, recomendação code review).
const STATUS_COLOR_MAP = { Apta: "green", Restrita: "amber", Bloqueada: "red" };

const KPI_DEFS = [
  { key: "gvf", color: "green", icon: "💧", label: "GVF", unit: "fração / %",
    value: (r) => (r.gvf < 1 ? pct(r.gvf) : dec(r.gvf)),
    badge: (r) => (r.envelopeStatus === "Apta" ? "Dentro do envelope" : r.envelopeStatus) },
  { key: "wlr", color: "blue", icon: "🌊", label: "WLR", unit: "m³/m³",
    value: (r) => fmt3.format(r.wlr),
    badge: (r) => (r.wlr < 0.45 ? "Dentro do envelope" : "Atenção") },
  { key: "gor", color: "purple", icon: "🔥", label: "GOR", unit: "Sm³/Sm³",
    value: (r) => dec(r.gor),
    badge: () => "Calculado" },
  { key: "iaj", color: "amber", icon: "⌖", label: "IAJ", unit: "0–100",
    value: (r) => String(r.iaj),
    badge: (r) => r.technicalStatus },
  { key: "status", icon: "🛡", label: "Status da Janela", unit: "decisão",
    color: (r) => STATUS_COLOR_MAP[r.technicalStatus] || "red",
    value: (r) => r.technicalStatus,
    badge: () => "Conforme critérios do MVP" },
  { key: "factor", color: "magenta", icon: "▣", label: "Fator sugerido", unit: "requer aprovação",
    value: (r) => fmt3.format(r.factorSuggested),
    badge: () => "Não aplicar sem aprovação" },
];

function pillClass(badgeText) {
  if (badgeText.includes("Atenção") || badgeText.includes("Restrita") || badgeText.includes("aprovação")) return "warn";
  if (badgeText.includes("Fora") || badgeText.includes("Bloqueada")) return "bad";
  return "ok";
}

function KpiCard({ def, r }) {
  const color = typeof def.color === "function" ? def.color(r) : def.color;
  const value = def.value(r);
  const badge = def.badge(r);
  return (
    <article className={`panel kpi-card ${color}`} data-testid={`kpi-${def.key}`}>
      <div className="kpi-top">
        <div className="kpi-icon">{def.icon}</div>
        <div>
          <div className="kpi-label">{def.label}</div>
          <div className="kpi-unit">{def.unit}</div>
        </div>
      </div>
      <div className="kpi-value">{value}</div>
      <span className={`pill ${pillClass(badge)}`}>{badge}</span>
    </article>
  );
}

export default function KpiCards({ r }) {
  return (
    <section className="kpi-grid" data-testid="kpi-grid">
      {KPI_DEFS.map((def) => <KpiCard key={def.key} def={def} r={r} />)}
    </section>
  );
}
