import React from "react";
import { fmt3 } from "@/calculations";

// Config object substitui 3 ternários encadeados (recomendação code review).
const STATUS_DECISION = {
  Apta:       { badgeClass: "ok",   title: "Janela Apta",       icon: "✅" },
  Restrita:   { badgeClass: "warn", title: "Janela Restrita",   icon: "⚠️" },
  Bloqueada:  { badgeClass: "bad",  title: "Janela Bloqueada",  icon: "⛔" },
};

export default function DecisionPanel({ r, input, onOpenReport, onDownloadState }) {
  const d = STATUS_DECISION[r.technicalStatus] || STATUS_DECISION.Bloqueada;
  return (
    <article className="panel decision-panel" data-testid="decision-panel">
      <div className="panel-head">
        <h2>Decisão Técnica</h2>
        <span className={`status-badge ${d.badgeClass}`} data-testid="decision-badge">{r.technicalStatus}</span>
      </div>
      <h3>{d.icon} {d.title}</h3>
      <p>
        IAJ atual: <strong>{r.iaj}</strong>. Envelope: <strong>{r.envelopeStatus}</strong>. Par selecionado: <strong>{input.comparisonPair}</strong>.
      </p>
      <ul>
        <li>✓ Referência do separador calculável por balanço de massas quando selecionada.</li>
        <li>✓ Fator sugerido calculado: <strong>{fmt3.format(r.factorSuggested)}</strong> — requer aprovação metrológica.</li>
        <li>⚠ Gas lift: {input.gasLift > 0 ? "informado e descontado no gás de HC." : "não confirmado; compensação não aplicada."}</li>
        <li>⚠ Rota operacional: inferida por banco/loop/tag; não declarada como confirmada por válvulas.</li>
        <li>ℹ FCS320/PVTPack: tratado como referência externa black-box nesta fase.</li>
      </ul>
      <div className="decision-actions">
        <button type="button" className="outline-button" data-testid="open-report" onClick={onOpenReport}>📄 Gerar relatório da análise</button>
        <button type="button" className="ghost-button" data-testid="download-state" onClick={onDownloadState}>Exportar JSON</button>
      </div>
    </article>
  );
}
