import React from "react";
import { fmt, fmt3 } from "@/calculations";

export default function HistoryTable({ history }) {
  return (
    <table className="data-table" data-testid="history-table">
      <thead>
        <tr><th>Janela</th><th>GVF</th><th>WLR</th><th>IAJ</th><th>Desvio HC</th><th>Status</th></tr>
      </thead>
      <tbody>
        {history.map((h) => (
          <tr key={h.t}>
            <td>{h.t}</td><td>{fmt3.format(h.gvf)}</td><td>{fmt3.format(h.wlr)}</td>
            <td>{h.iaj}</td><td>{fmt.format(h.devHC)}%</td>
            <td><span className={`pill ${h.status === "Apta" ? "ok" : "warn"}`}>{h.status}</span></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
