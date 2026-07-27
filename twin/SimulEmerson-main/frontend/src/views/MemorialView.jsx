import React, { useMemo } from "react";
import { buildMemorial, downloadFile } from "@/calculations";

export default function MemorialView({ state }) {
  const md = useMemo(() => buildMemorial(state), [state]);
  return (
    <section data-testid="memorial-view" className="active-view">
      <section className="panel section-header">
        <h2>Memorial Auditável</h2>
        <p>Registro técnico gerado automaticamente a partir da janela ativa, com cálculo, premissas, limitações e rastreabilidade.</p>
      </section>
      <article className="panel" style={{ padding: 16 }}>
        <div className="panel-head">
          <h3>Memorial gerado</h3>
          <button type="button" className="outline-button" data-testid="download-memorial" onClick={() => downloadFile("memorial_twin_mpfm_janela.md", md)}>Baixar .md</button>
        </div>
        <pre className="memorial-output" data-testid="memorial-output">{md}</pre>
      </article>
    </section>
  );
}
