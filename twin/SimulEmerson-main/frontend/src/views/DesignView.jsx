import React from "react";

export default function DesignView() {
  return (
    <section data-testid="design-view" className="active-view">
      <section className="panel section-header">
        <h2>Mockups de Referência</h2>
        <p>Imagens finais de alta resolução para reprodução fiel do layout no desenvolvimento.</p>
      </section>
      <section className="mockup-grid">
        <img src="/mockup_light.png" alt="Mockup claro" />
        <img src="/mockup_dark.png" alt="Mockup escuro" />
      </section>
    </section>
  );
}
