import React from "react";

export default function TopBar({ pageTitle, pageSubtitle, onToggleTheme, apiStatus }) {
  return (
    <header className="topbar">
      <div>
        <div className="title-row">
          <h1 data-testid="page-title">{pageTitle}</h1>
          <span className="env-pill">Protótipo operacional</span>
        </div>
        <p className="page-subtitle" data-testid="page-subtitle">{pageSubtitle}</p>
      </div>
      <div className="top-actions">
        <span className="system-status" data-testid="api-status"><i />{apiStatus}</span>
        <span className="system-status"><i />Ambiente: <strong>PROTÓTIPO</strong></span>
        <button
          type="button"
          className="icon-button"
          data-testid="theme-toggle"
          title="Alternar tema"
          onClick={onToggleTheme}
        >
          ◐
        </button>
        <button type="button" className="icon-button badge" title="Notificações">
          🔔<b>3</b>
        </button>
        <div className="user-chip">
          <span>AB</span>
          <div><strong>Alex Braga</strong><em>Eng. de Medição</em></div>
        </div>
      </div>
    </header>
  );
}
