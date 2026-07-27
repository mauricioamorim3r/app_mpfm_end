import React, { useState } from "react";
import { fmt3 } from "@/calculations";
import PVTCatalogTable from "@/components/PVTCatalogTable";
import PVTModal from "@/components/PVTModal";
import { usePvtCatalog } from "@/hooks/usePvtCatalog";

export default function PVTView({ pvt }) {
  const { catalog, create } = usePvtCatalog();
  const [modalOpen, setModalOpen] = useState(false);

  const handleSave = async (payload) => {
    await create(payload);
    setModalOpen(false);
  };

  const props = [
    ["SF_sep→tank", pvt.SF_sep_tank],
    ["ΔRs_sep→tank", pvt.deltaRs_sep_tank],
    ["ρ óleo STO", `${pvt.rho_oil_STO} kg/m³`],
    ["ρ gás std", `${fmt3.format(pvt.rho_gas_std)} kg/Sm³`],
    ["Status", pvt.status],
  ];

  return (
    <section data-testid="pvt-view" className="active-view">
      <section className="panel section-header">
        <h2>PVT / EOS Lab</h2>
        <p>Catálogo operacional de PVT, shrinkage, gás flash, densidades e rastreabilidade da origem dos dados.</p>
      </section>
      <section className="cards-3">
        <article className="panel">
          <h3>Fonte ativa</h3>
          <div style={{ marginTop: 10 }}>
            <p><strong>{pvt.source}</strong></p>
            <p>Fluido: {pvt.fluidId}</p>
            <p>EOS: {pvt.eos}</p>
            <p>Arquivo nativo PVTPack/PVTSim: <strong>{pvt.nativeFile ? "disponível" : "indisponível"}</strong></p>
          </div>
        </article>
        <article className="panel">
          <h3>Propriedades PVT</h3>
          <div className="quality-list">
            {props.map(([a, b]) => (
              <div key={a} className="quality-item">
                <span className="status-dot ok">✓</span>
                <strong>{a}</strong>
                <span>{b}</span>
              </div>
            ))}
          </div>
        </article>
        <article className="panel">
          <h3>Modo EOS</h3>
          <p><strong>independent_validation</strong></p>
          <p>PVTPack nativo indisponível nesta fase. Motor opcional preparado para SRK/Peneloux e NeqSim.</p>
        </article>
      </section>

      <article className="panel" style={{ padding: 16, marginTop: 14 }}>
        <div className="panel-head">
          <h3>Catálogo PVT — registros</h3>
          <button type="button" className="outline-button" data-testid="pvt-new" onClick={() => setModalOpen(true)}>+ Nova amostra</button>
        </div>
        <PVTCatalogTable catalog={catalog} />
      </article>

      {modalOpen && <PVTModal onSave={handleSave} onClose={() => setModalOpen(false)} />}
    </section>
  );
}
