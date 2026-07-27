import React from "react";
import { NAV_ITEMS, TOP_PSEUDO } from "@/lib/constants";

export default function Sidebar({ activeView, setActiveView, collapsed, onToggleCollapse }) {
  const all = [...TOP_PSEUDO, ...NAV_ITEMS];
  return (
    <aside className="sidebar" aria-label="Navegação principal" data-testid="sidebar">
      <div className="brand">
        <div className="brand-mark">◇</div>
        <div>
          <strong>Twin MPFM</strong>
          <span>Multi Phase Meter</span>
        </div>
      </div>
      <nav className="nav-list" data-testid="main-nav">
        {all.map(([view, icon, label], idx) => {
          const isActive = view === activeView;
          const testId = view !== "none" ? `nav-${view}` : `nav-pseudo-${idx}`;
          return (
            <button
              key={`${view}-${idx}`}
              type="button"
              data-testid={testId}
              className={`nav-item ${isActive ? "active" : ""}`}
              onClick={() => view !== "none" && setActiveView(view)}
            >
              <span className="nav-icon">{icon}</span>
              <span className="nav-label">{label}</span>
            </button>
          );
        })}
      </nav>
      <button
        type="button"
        data-testid="collapse-menu"
        className="ghost-button sidebar-collapse"
        onClick={onToggleCollapse}
      >
        {collapsed ? "›" : "‹ Recolher menu"}
      </button>
      <div className="sidebar-foot">
        <span>v4.0.0 • Build 2026.06</span>
        <span>FCS320: referência externa</span>
      </div>
    </aside>
  );
}
