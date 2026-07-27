import React from "react";

export default function PVTCatalogTable({ catalog }) {
  return (
    <table className="data-table" data-testid="pvt-catalog-table">
      <thead>
        <tr><th>Fluido</th><th>Fonte</th><th>EOS</th><th>SF</th><th>ΔRs</th><th>ρ óleo STO</th><th>Status</th><th>Criado</th></tr>
      </thead>
      <tbody>
        {catalog.length === 0 && (
          <tr><td colSpan={8} style={{ color: "var(--muted)", padding: 12 }}>
            Sem amostras cadastradas. Use &ldquo;+ Nova amostra&rdquo;.
          </td></tr>
        )}
        {catalog.map((p) => (
          <tr key={p.id}>
            <td>{p.fluid_id}</td><td>{p.source || "—"}</td><td>{p.eos || "—"}</td>
            <td>{p.sf_sep_tank ?? "—"}</td><td>{p.delta_rs_sep_tank ?? "—"}</td>
            <td>{p.rho_oil_sto ?? "—"}</td><td>{p.status || "—"}</td>
            <td>{(p.created_at || "").slice(0, 19).replace("T", " ")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
