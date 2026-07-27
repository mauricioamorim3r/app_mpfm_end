import React from "react";
import FilterBar from "@/components/FilterBar";
import KpiCards from "@/components/KpiCards";
import EnvelopeChart from "@/components/EnvelopeChart";
import DecisionPanel from "@/components/DecisionPanel";
import ComparisonCards from "@/components/ComparisonCards";
import QualityList from "@/components/QualityList";
import AlertsList from "@/components/AlertsList";
import HistoryTable from "@/components/HistoryTable";
import HistoryStrip from "@/components/HistoryStrip";
import { DEFAULT_INPUT } from "@/lib/constants";

export default function ConsultorView({
  input, setInput, separator, pvt, state,
  runAnalysis, openReport, downloadStateJson, exportCsv,
}) {
  const r = state.results;
  return (
    <section data-testid="consultor-view" className="active-view">
      <FilterBar input={input} setInput={setInput} onRun={runAnalysis} />
      <KpiCards r={r} />
      <section className="main-grid">
        <article className="panel chart-panel">
          <div className="panel-head">
            <h2>Mapa de Aplicabilidade GVF × WLR</h2>
            <span className="info-dot" title="Mapa de envelope operacional baseado em GVF e WLR">i</span>
            <button type="button" className="mini-button" data-testid="reset-scenario" onClick={() => setInput(DEFAULT_INPUT)}>Resetar cenário</button>
          </div>
          <div className="envelope-chart" data-testid="envelope-chart" role="img" aria-label="Mapa GVF por WLR">
            <EnvelopeChart id="envelopeChart" height={330} r={r} history={state.history} />
          </div>
          <div className="chart-legend">
            <span className="legend apta" />Apta
            <span className="legend restrita" />Restrita
            <span className="legend fora" />Fora do Envelope
            <span className="legend atual" />Operação Atual
          </div>
        </article>
        <DecisionPanel r={r} input={input} onOpenReport={openReport} onDownloadState={downloadStateJson} />
      </section>
      <section className="lower-grid">
        <article className="panel">
          <div className="panel-head"><h2>Comparações Disponíveis</h2><span className="info-dot">i</span></div>
          <ComparisonCards r={r} />
        </article>
        <article className="panel">
          <div className="panel-head"><h2>Qualidade de Dados</h2><span className="info-dot">i</span></div>
          <QualityList input={input} pvt={pvt} />
        </article>
        <article className="panel">
          <div className="panel-head"><h2>Alertas RCA</h2><span className="info-dot">i</span></div>
          <AlertsList r={r} input={input} />
        </article>
        <article className="panel">
          <div className="panel-head"><h2>Últimas Janelas</h2>
            <button type="button" className="mini-button" data-testid="download-csv" onClick={exportCsv}>CSV</button>
          </div>
          <HistoryTable history={state.history} />
        </article>
      </section>
      <section className="panel history-strip-panel">
        <div className="panel-head"><h2>Histórico de Janelas</h2><span className="info-dot">i</span></div>
        <HistoryStrip history={state.history} />
      </section>
    </section>
  );
}
