import React from "react";
import EnvelopeChart from "@/components/EnvelopeChart";
import { fmt3 } from "@/calculations";

export default function EnvelopeView({ r, history }) {
  const params = [
    ["GVF atual", fmt3.format(r.gvf)],
    ["WLR atual", fmt3.format(r.wlr)],
    ["Status envelope", r.envelopeStatus],
    ["IAJ", r.iaj],
    ["Critério", "Apta / Restrita / Bloqueada"],
    ["Uso", "Triagem e decisão operacional"],
  ];
  return (
    <section data-testid="envelope-view" className="active-view">
      <section className="panel section-header">
        <h2>Envelope Operacional</h2>
        <p>Simulação tipo calculadora: altere GVF/WLR por P, T e vazões para verificar aplicabilidade, margem operacional e risco de janela.</p>
      </section>
      <section className="main-grid">
        <article className="panel chart-panel">
          <div className="envelope-chart large">
            <EnvelopeChart id="envelopeChartStandalone" height={500} r={r} history={history} />
          </div>
          <div className="chart-legend">
            <span className="legend apta" />Apta
            <span className="legend restrita" />Restrita
            <span className="legend fora" />Fora do Envelope
            <span className="legend atual" />Operação Atual
          </div>
        </article>
        <article className="panel" style={{ padding: 16 }}>
          <h3>Parâmetros do envelope</h3>
          <div className="quality-list">
            {params.map(([a, b]) => (
              <div key={a} className="quality-item">
                <span className="status-dot ok">•</span>
                <strong>{a}</strong>
                <span>{b}</span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </section>
  );
}
