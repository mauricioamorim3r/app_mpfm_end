import React from "react";
import { buildMemorial, downloadFile } from "@/calculations";

export default function ReportDialog({ state, onClose }) {
  const md = buildMemorial(state);
  return (
    <dialog open className="report-dialog" data-testid="report-dialog">
      <form method="dialog">
        <div className="panel-head">
          <h2>Relatório da Análise</h2>
          <button type="button" className="icon-button" onClick={onClose}>×</button>
        </div>
        <pre className="memorial-output report" data-testid="report-text">{md}</pre>
        <div className="dialog-actions">
          <button
            type="button"
            className="primary-button"
            data-testid="download-report"
            onClick={() => downloadFile("memorial_twin_mpfm_janela.md", md)}
          >
            Baixar relatório .md
          </button>
          <button type="button" className="ghost-button" onClick={onClose}>Fechar</button>
        </div>
      </form>
    </dialog>
  );
}
