import React from "react";

const RCA_ROWS = [
  ["Gas lift não confirmado", "Média", "Não aplicar compensação; registrar premissa no memorial"],
  ["Rota inferida", "Média", "Solicitar confirmação operacional quando disponível"],
  ["PVTPack nativo indisponível", "Baixa", "Usar PVT tabulado e validação independente"],
  ["Água pouco representativa", "Média", "Não aprovar Kw definitivo sem massa representativa"],
  ["Fator sugerido requer aprovação", "Alta", "Submeter para responsável metrológico"],
];

export default function RCAView() {
  return (
    <section data-testid="rca-view" className="active-view">
      <section className="panel section-header">
        <h2>RCA / Alertas</h2>
        <p>Fila operacional de anomalias, causa provável, severidade e ação recomendada.</p>
      </section>
      <article className="panel" style={{ padding: 16 }}>
        <table className="data-table" data-testid="rca-table">
          <thead><tr><th>Alerta</th><th>Severidade</th><th>Ação recomendada</th></tr></thead>
          <tbody>{RCA_ROWS.map((r) => (<tr key={r[0]}><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td></tr>))}</tbody>
        </table>
      </article>
    </section>
  );
}
