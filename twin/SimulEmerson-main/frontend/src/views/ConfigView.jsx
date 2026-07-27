import React, { useRef, useState } from "react";
import { api } from "@/lib/api";
import { CONSTANTS } from "@/calculations";

export default function ConfigView({ lastAnalysisId }) {
  const [importResult, setImportResult] = useState("");
  const fileRef = useRef(null);

  const upload = async () => {
    const f = fileRef.current?.files?.[0];
    if (!f) { setImportResult("Selecione um arquivo .xlsx ou .xlsm."); return; }
    setImportResult("Importando...");
    try {
      const data = await api.importMpfm(f);
      setImportResult(JSON.stringify(data, null, 2));
    } catch (err) {
      setImportResult(`Falha na importação: ${err.message}`);
    }
  };

  return (
    <section data-testid="config-view" className="active-view">
      <section className="panel section-header">
        <h2>Configurações</h2>
        <p>Constantes, premissas e opções de execução do MVP.</p>
      </section>
      <article className="panel" style={{ padding: 16 }}>
        <table className="data-table" data-testid="config-table">
          <tbody>
            {Object.entries(CONSTANTS).map(([k, v]) => (
              <tr key={k}><th>{k}</th><td>{String(v)}</td></tr>
            ))}
          </tbody>
        </table>
      </article>
      <article className="panel" style={{ padding: 16, marginTop: 14 }}>
        <div className="panel-head">
          <h3>Integração / Importação</h3>
          <span className="pill ok" data-testid="last-analysis-id">
            {lastAnalysisId ? `análise #${lastAnalysisId.slice(0, 8)} salva` : "sem análise salva"}
          </span>
        </div>
        <div className="import-box" style={{ marginTop: 12 }}>
          <p>Importe planilhas mensais MPFM (.xlsx/.xlsm) para o backend persistir registros históricos.</p>
          <input ref={fileRef} type="file" accept=".xlsx,.xlsm" data-testid="mpfm-file" />
          <button type="button" className="outline-button" data-testid="upload-mpfm" onClick={upload}>Importar planilha MPFM</button>
          <pre className="mini-log" data-testid="import-result">{importResult}</pre>
        </div>
      </article>
    </section>
  );
}
