import React from "react";
import { fmt } from "@/calculations";

function Spark({ status }) {
  const color = status === "Apta" ? "var(--green)" : "var(--amber)";
  const pts = Array.from({ length: 10 }, (_, i) => `${i * 11},${18 - (Math.sin(i * 1.4) + 1) * 6 - (i % 3)}`).join(" ");
  const lastY = pts.split(" ").pop().split(",")[1];
  return (
    <svg className="spark" viewBox="0 0 100 24">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" />
      <circle cx="99" cy={lastY} r="2" fill={color} />
    </svg>
  );
}

export default function HistoryStrip({ history }) {
  return (
    <div className="history-strip" data-testid="history-strip">
      {history.map((h, i) => (
        <div key={h.t} className={`history-card ${i === history.length - 1 ? "active" : ""}`}>
          <strong>{h.t}</strong>
          <div style={{ marginTop: 6 }}>
            <span className={`pill ${h.status === "Apta" ? "ok" : "warn"}`}>{h.status}</span>
          </div>
          <div style={{ marginTop: 4, fontSize: 12, color: "var(--muted)" }}>Desvio: {fmt.format(h.devHC)}%</div>
          <Spark status={h.status} />
        </div>
      ))}
    </div>
  );
}
