import React from "react";
import { fmt3 } from "@/calculations";

export default function AlertsList({ r, input }) {
  const alerts = [];
  if (r.envelopeStatus !== "Apta") alerts.push(["bad", "Envelope em atenção", `Status ${r.envelopeStatus}; revisar aplicabilidade.`]);
  if (r.gvf > 0.55) alerts.push(["bad", "Proximidade de limite por GVF", `GVF ${fmt3.format(r.gvf)}.`]);
  if (input.gasLift <= 0) alerts.push(["warn", "Gas lift não confirmado", "Compensação de gás lift não aplicada."]);
  alerts.push(["warn", "Roteamento inferido", "Alinhamento real de válvulas não disponível."]);
  if (input.qw < 1) alerts.push(["warn", "Água não representativa", "Baixa água pode limitar avaliação de Kw/água."]);
  if (Math.abs(r.enHC) > 1) alerts.push(["bad", "Erro normalizado En acima de 1", `En_HC = ${fmt3.format(r.enHC)}.`]);
  else alerts.push(["ok", "Compatibilidade por En", `En_HC = ${fmt3.format(r.enHC)}.`]);
  return (
    <div className="alert-list" data-testid="alert-list">
      {alerts.map(([type, title, detail]) => (
        <div key={`${type}-${title}`} className={`alert-item ${type}`}>
          <strong>{title}</strong>
          <span>{detail}</span>
        </div>
      ))}
    </div>
  );
}
