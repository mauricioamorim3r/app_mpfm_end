import ConsultorView from "@/views/ConsultorView";
import BalanceView from "@/views/BalanceView";
import PVTView from "@/views/PVTView";
import EnvelopeView from "@/views/EnvelopeView";
import RCAView from "@/views/RCAView";
import MemorialView from "@/views/MemorialView";
import ConfigView from "@/views/ConfigView";
import DesignView from "@/views/DesignView";

/**
 * Roteador da SPA — single source of truth do mapping view→componente.
 * Cada entrada recebe `ctx` (estado global) e devolve o elemento React.
 */
export const VIEW_ROUTES = {
  consultorView: (ctx) => (
    <ConsultorView
      input={ctx.input} setInput={ctx.setInput}
      separator={ctx.separator} pvt={ctx.pvt} state={ctx.state}
      runAnalysis={ctx.runAnalysis}
      openReport={ctx.openReport}
      downloadStateJson={ctx.downloadStateJson}
      exportCsv={ctx.exportCsv}
    />
  ),
  balanceView: (ctx) => <BalanceView separator={ctx.separator} setSeparator={ctx.setSeparator} />,
  pvtView: (ctx) => <PVTView pvt={ctx.pvt} />,
  envelopeView: (ctx) => <EnvelopeView r={ctx.state.results} history={ctx.history} />,
  rcaView: () => <RCAView />,
  memorialView: (ctx) => <MemorialView state={ctx.state} />,
  configView: (ctx) => <ConfigView lastAnalysisId={ctx.lastAnalysisId} />,
  designView: () => <DesignView />,
};

export default function AppRouter({ activeView, ctx }) {
  const render = VIEW_ROUTES[activeView] || VIEW_ROUTES.consultorView;
  return render(ctx);
}
