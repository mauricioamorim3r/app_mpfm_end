// Twin MPFM v4 — orquestrador.
// Componentes em /components, views em /views, cálculos em /calculations.js,
// HTTP em /lib/api.js, hooks em /hooks/*.
import React, { useMemo, useState } from "react";
import "@/App.css";

import { computeResults, downloadFile } from "@/calculations";
import {
  DEFAULT_HISTORY, DEFAULT_INPUT, DEFAULT_PVT, DEFAULT_SEPARATOR, NAV_ITEMS,
} from "@/lib/constants";

import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import ReportDialog from "@/components/ReportDialog";
import AppRouter from "@/AppRouter";
import { useTheme } from "@/hooks/useTheme";
import { useApiConnection } from "@/hooks/useApiConnection";

function App() {
  const { theme, toggle: toggleTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [activeView, setActiveView] = useState("consultorView");
  const [input, setInput] = useState(DEFAULT_INPUT);
  const [separator, setSeparator] = useState(DEFAULT_SEPARATOR);
  const [pvt] = useState(DEFAULT_PVT);
  const [history] = useState(DEFAULT_HISTORY);
  const [reportOpen, setReportOpen] = useState(false);

  const { status: apiStatus, lastAnalysisId, runAnalysis: runAnalyze } = useApiConnection();

  const results = useMemo(() => computeResults(input, separator), [input, separator]);
  const state = { input, separator, pvt, history, results };

  const runAnalysis = () => runAnalyze({ input, separator, pvt });

  const downloadStateJson = () => downloadFile(
    "twin_mpfm_estado_analise.json",
    JSON.stringify({ analysis_id: lastAnalysisId, input, separator, pvt, results }, null, 2),
    "application/json;charset=utf-8",
  );

  const exportCsv = () => {
    const head = "janela,gvf,wlr,iaj,desvio_hc,status\n";
    const body = history.map((h) => `${h.t},${h.gvf},${h.wlr},${h.iaj},${h.devHC},${h.status}`).join("\n");
    downloadFile("twin_mpfm_historico_janelas.csv", head + body, "text/csv;charset=utf-8");
  };

  const meta = NAV_ITEMS.find((n) => n[0] === activeView) || NAV_ITEMS[0];
  const pageTitle = meta[3];
  const pageSubtitle = meta[4];

  // Contexto entregue ao roteador (única fonte da verdade)
  const ctx = {
    input, setInput, separator, setSeparator, pvt, history, state,
    lastAnalysisId, runAnalysis,
    openReport: () => setReportOpen(true),
    downloadStateJson, exportCsv,
  };

  return (
    <div className={`app-shell ${collapsed ? "collapsed" : ""}`} id="app" data-theme={theme}>
      <Sidebar
        activeView={activeView}
        setActiveView={setActiveView}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((c) => !c)}
      />
      <main className="workspace">
        <TopBar
          pageTitle={pageTitle}
          pageSubtitle={pageSubtitle}
          onToggleTheme={toggleTheme}
          apiStatus={apiStatus}
        />

        <AppRouter activeView={activeView} ctx={ctx} />

        <footer className="workspace-foot">
          <span>Condição padrão Brasil: 20 °C / 0,101325 MPa abs</span>
          <span>FCS320 black-box | PVTPack nativo indisponível | Rota inferida</span>
        </footer>
      </main>

      {reportOpen && <ReportDialog state={state} onClose={() => setReportOpen(false)} />}
    </div>
  );
}

export default App;
