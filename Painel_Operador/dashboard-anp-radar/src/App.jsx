import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bell,
  BrainCircuit,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  Database,
  FileArchive,
  FileCode2,
  FileSearch,
  FlaskConical,
  Gauge,
  Layers3,
  RadioTower,
  Ruler,
  Search,
  ShieldCheck,
  Send,
  SlidersHorizontal,
  Table2,
  Timer,
  Wrench,
  X,
} from "lucide-react";
import React, { useEffect, useMemo, useState } from "react";
import initialDashboardData from "./data/dashboard-data.json";

const statusLabel = {
  ok: "OK",
  warn: "Atenção",
  critical: "Crítico",
  open: "Aberta",
  resolved: "Baixada",
  ignored: "Ignorada",
  not_loaded: "Sem carga",
};

const severityLabel = {
  critical: "Crítico",
  warn: "Atenção",
  ok: "OK",
};

const evidenceStateLabel = {
  confirmed: "Confirmada",
  supporting: "Apoio textual",
  candidate: "Candidata",
  missing: "Sem evidência",
};

const proposalStatusLabel = {
  pending_authorization: "Pendente",
  authorized: "Autorizada",
  rejected: "Rejeitada",
  deferred: "Adiada",
};

const providerModels = {
  openai: ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"],
  anthropic: ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"],
  google: ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"],
};

const defaultAiConfig = {
  schemaVersion: 1,
  enabled: false,
  activeProvider: "openai",
  providers: {
    openai: { label: "OpenAI", model: "gpt-4.1", apiKey: "", apiKeySet: false },
    anthropic: { label: "Claude", model: "claude-3-5-sonnet-latest", apiKey: "", apiKeySet: false },
    google: { label: "Gemini", model: "gemini-1.5-pro", apiKey: "", apiKeySet: false },
  },
  permissions: {
    readConfiguredFolders: true,
    extractDocuments: true,
    writeDrafts: true,
    copyMoveFiles: false,
    requireApprovalForFileOps: true,
    auditLog: true,
  },
  contextManifestPath: "",
  auditLogPath: "",
};

const graphAreas = [
  ["Fechamento diário", "ativo", "ativo", "Óleo e gás por dia, com seleção de data e comparação visual."],
  ["Raw x XML x ANP", "ativo", "ativo", "Tabela interativa por ponto, família, busca e camadas selecionáveis."],
  ["Limites/PAM/faixa", "ativo", "ativo", "Envelope por ponto com mínimo, máximo, PAM e posição do valor atual."],
  ["Incerteza", "parcial", "parcial", "Área pronta; cálculo diário ainda depende de memória de cálculo/fonte específica."],
  ["Eventos x evidências", "ativo", "ativo", "Tabela auditável de alteração de parâmetro contra evidências documentais."],
  ["Dossiê do ponto", "parcial", "parcial", "Resumo existe; anexos/certificados/histórico completo ainda serão ligados."],
  ["Banco SQLite", "ativo", "ativo", "Base local gerada em data/radar-anp.sqlite para SQL, auditoria e IA."],
  ["Propostas auditáveis", "ativo", "ativo", "Achados viram propostas com evidência, autorização e log antes de qualquer gravação."],
  ["Pergunte ao Radar", "ativo", "ativo", "Campo global em todas as telas, com resposta local auditável e LLM quando a chave está habilitada."],
];

const viewTitles = {
  operacao: "Fechamento diário de medição e recebimento ANP",
  config: "Configuração das fontes de dados",
  trilha: "Trilha E2E e banco operacional",
  prazos: "Prazos, falhas e obrigações regulatórias",
  propostas: "Propostas rastreáveis para autorização",
  calendario: "Calendário de cargas e pendências",
};

function number(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function shortDate(value) {
  if (!value) return "-";
  const [year, month, day] = value.split("-");
  return `${day}/${month}`;
}

function fullDate(value) {
  if (!value) return "-";
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

function fullDateTime(value) {
  if (!value) return "-";
  const [datePart, timePart = ""] = value.split("T");
  return `${fullDate(datePart)} ${timePart.slice(0, 5)}`.trim();
}

function proposalValue(value, unit) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return `${value}${unit ? ` ${unit}` : ""}`;
}

function sumValues(rows, field) {
  let found = false;
  const total = rows.reduce((acc, row) => {
    const value = Number(row?.[field]);
    if (Number.isNaN(value)) return acc;
    found = true;
    return acc + value;
  }, 0);
  return found ? total : null;
}

function diffValues(left, right) {
  if (left === null || left === undefined || right === null || right === undefined) return null;
  const leftNumber = Number(left);
  const rightNumber = Number(right);
  if (Number.isNaN(leftNumber) || Number.isNaN(rightNumber)) return null;
  return leftNumber - rightNumber;
}

function weightedAverage(rows) {
  const totals = rows.reduce(
    (acc, row) => {
      const count = Number(row?.count) || 0;
      const average = Number(row?.avg);
      if (!count || Number.isNaN(average)) return acc;
      return { value: acc.value + average * count, count: acc.count + count };
    },
    { value: 0, count: 0 },
  );
  return totals.count ? totals.value / totals.count : null;
}

function firstAvailable(...values) {
  return values.find((value) => value !== null && value !== undefined && !Number.isNaN(Number(value))) ?? null;
}

function modelRows(data, selectedDate, domains, kinds) {
  const domainSet = new Set(domains);
  const kindSet = new Set(kinds);
  return (data.measurementModels?.dailyAggregates || []).filter((row) => {
    if (!row || typeof row !== "object") return false;
    return row.date === selectedDate && domainSet.has(row.domain) && kindSet.has(row.kind);
  });
}

function measurementInsights(data, selectedDate) {
  const comparisons = Array.isArray(data.comparisons) ? data.comparisons : [];
  const closing = Array.isArray(data.closing) ? data.closing : [];
  const dateRows = comparisons.filter((row) => row.date === selectedDate);
  const oilRows = dateRows.filter((row) => row.fluid === "Oleo" || /oleo|óleo/i.test(row.familyName || ""));
  const gasRows = dateRows.filter((row) => row.fluid === "Gas" || /gas/i.test(row.familyName || ""));
  const allOilRows = comparisons.filter((row) => row.fluid === "Oleo" || /oleo|óleo/i.test(row.familyName || ""));
  const allGasRows = comparisons.filter((row) => row.fluid === "Gas" || /gas/i.test(row.familyName || ""));
  const closingRow = closing.find((row) => row.date === selectedDate) || {};
  const fiscalOilModels = modelRows(data, selectedDate, ["fiscal_metering"], ["oil"]);
  const fiscalGasModels = modelRows(data, selectedDate, ["fiscal_metering"], ["gas"]);
  const mpfmOilModels = modelRows(data, selectedDate, ["well_mpfm", "riser_mpfm", "flowline"], ["oil"]);
  const mpfmGasModels = modelRows(data, selectedDate, ["well_mpfm", "riser_mpfm", "flowline"], ["gas"]);
  const injectionGasModels = modelRows(data, selectedDate, ["gas_injection"], ["gas", "pressure", "choke"]);
  const productionOilModels = modelRows(data, selectedDate, ["production_overview", "production_well", "quick_look"], ["oil"]);
  const productionGasModels = modelRows(data, selectedDate, ["production_overview", "production_well", "quick_look"], ["gas"]);
  const modelSummary = data.measurementModels?.summary || {};
  return {
    selectedDate,
    fiscalVsMultiphase: {
      oilFiscal: firstAvailable(weightedAverage(fiscalOilModels), sumValues(oilRows, "anpCorrigido"), sumValues(oilRows, "xmlCorrigido")),
      oilRaw: firstAvailable(weightedAverage(mpfmOilModels), sumValues(oilRows, "rawCorrigido")),
      gasFiscal: firstAvailable(weightedAverage(fiscalGasModels), sumValues(gasRows, "anpCorrigido"), sumValues(gasRows, "xmlCorrigido")),
      gasRaw: firstAvailable(weightedAverage(mpfmGasModels), sumValues(gasRows, "rawCorrigido")),
      oilRows: oilRows.length,
      gasRows: gasRows.length,
      modelSamples: [...fiscalOilModels, ...fiscalGasModels, ...mpfmOilModels, ...mpfmGasModels].reduce((total, row) => total + (Number(row.count) || 0), 0),
    },
    gasBalance: {
      dayGas: firstAvailable(weightedAverage(fiscalGasModels), Number(closingRow.totalGas), sumValues(gasRows, "anpCorrigido")),
      monthGas: sumValues(closing, "totalGas"),
      injectionAverage: weightedAverage(injectionGasModels),
      productionAverage: weightedAverage(productionGasModels),
      pendingRows: gasRows.filter((row) => !row.rawOk || !row.anpOk).length,
      totalGasRows: allGasRows.length,
      modelSamples: [...fiscalGasModels, ...injectionGasModels, ...productionGasModels].reduce((total, row) => total + (Number(row.count) || 0), 0),
    },
    offloading: {
      dayOil: firstAvailable(weightedAverage(fiscalOilModels), Number(closingRow.totalOil), sumValues(oilRows, "anpCorrigido")),
      monthOil: sumValues(closing, "totalOil"),
      productionAverage: weightedAverage(productionOilModels),
      fiscalRows: allOilRows.length,
      sourceLoaded: fiscalOilModels.length > 0 || productionOilModels.length > 0,
      modelSamples: [...fiscalOilModels, ...productionOilModels].reduce((total, row) => total + (Number(row.count) || 0), 0),
    },
    production: {
      files: (data.files?.length || 0) + (modelSummary.files || 0),
      comparisons: comparisons.length + (modelSummary.signals || 0),
      alerts: data.alerts?.length || 0,
      proposals: data.changeProposals?.length || 0,
      loadedDays: data.operationalCalendar?.summary?.loaded || data.meta?.sourceDates?.length || 0,
      openPendencies: data.operationalCalendar?.summary?.openPendencies || 0,
      modelRows: modelSummary.rows || 0,
      modelNumericRows: modelSummary.numericRows || 0,
      modelSignals: modelSummary.signals || 0,
      modelAggregatesPublished: modelSummary.dailyAggregatesPublished || 0,
      modelAggregatesTotal: modelSummary.dailyAggregatesTotal || 0,
      modelOutputTruncated: Boolean(modelSummary.outputTruncated),
      modelWarnings: Array.isArray(modelSummary.warnings) ? modelSummary.warnings : [],
    },
  };
}

function StatusPill({ status }) {
  return (
    <span className={`status status-${status}`}>
      {statusLabel[status] || severityLabel[status] || proposalStatusLabel[status] || evidenceStateLabel[status] || status}
    </span>
  );
}

function Kpi({ icon: Icon, label, value, tone, helper }) {
  return (
    <section className={`kpi kpi-${tone || "neutral"}`}>
      <div className="kpi-icon">
        <Icon size={18} />
      </div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        {helper ? <small>{helper}</small> : null}
      </div>
    </section>
  );
}

function OperatorPanelHealthPanel({ health }) {
  const exports = Array.isArray(health?.exports) ? health.exports : [];
  if (!health) return null;
  return (
    <section className={`panel operator-health-panel operator-health-${health.status || "warn"}`}>
      <div className="panel-head">
        <div>
          <span className="eyebrow">Fonte prioritária</span>
          <h2>Painel do Operador</h2>
        </div>
        <StatusPill status={health.status || "warn"} />
      </div>
      <div className="operator-health-summary">
        <div><span>Prontos</span><strong>{health.ready || 0}/{health.required || exports.length}</strong></div>
        <div><span>Arquivos faltando</span><strong>{health.missingFiles || 0}</strong></div>
        <div><span>Informação faltando</span><strong>{health.missingInformation || 0}</strong></div>
      </div>
      <div className="operator-export-list">
        {exports.map((item) => (
          <article className={`operator-export operator-export-${item.status || "warn"}`} key={item.id}>
            <StatusPill status={item.status || "warn"} />
            <div>
              <strong>{item.label}</strong>
              <span>{item.message}</span>
              <small>{item.path || item.fileName}</small>
            </div>
            <em>{item.rows || 0} linhas{item.latestDate ? ` · ${fullDate(item.latestDate)}` : ""}</em>
          </article>
        ))}
      </div>
      <p className="panel-note">Esse indicador permanece visível até os arquivos/colunas obrigatórios do Painel do Operador estarem completos ou a pendência ser tratada na fonte.</p>
    </section>
  );
}

function Pipeline({ selectedDate, rows, files }) {
  const dateFiles = files.filter((item) => item.date === selectedDate);
  const familyCount = new Set(dateFiles.map((item) => item.family)).size;
  const rawOk = rows.filter((row) => row.rawOk).length;
  const anpOk = rows.filter((row) => row.anpOk).length;
  const zipCount = dateFiles.filter((item) => item.kind === "zip").length;
  const nodes = [
    {
      icon: Database,
      title: "Raw CV/IHM",
      value: `${rawOk}/${rows.length}`,
      detail: "Run_Daily e fonte estimada",
      status: rawOk === rows.length ? "ok" : "warn",
    },
    {
      icon: Table2,
      title: "Checklist interno",
      value: "ponte",
      detail: "conciliação diária",
      status: "ok",
    },
    {
      icon: FileCode2,
      title: "XML gerado",
      value: `${familyCount}/4`,
      detail: "001, 002, 003, 004",
      status: familyCount === 4 ? "ok" : "critical",
    },
    {
      icon: FileArchive,
      title: "ZIP enviado",
      value: `${zipCount}`,
      detail: "evidência em 05 - XML",
      status: zipCount >= 4 ? "ok" : "warn",
    },
    {
      icon: RadioTower,
      title: "Painel ANP",
      value: `${anpOk}/${rows.length}`,
      detail: "export recebido",
      status: anpOk === rows.length ? "ok" : "critical",
    },
  ];
  return (
    <section className="panel pipeline-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">End-to-end</span>
          <h2>Trilha operacional de {fullDate(selectedDate)}</h2>
        </div>
        <StatusPill status={nodes.some((n) => n.status === "critical") ? "critical" : nodes.some((n) => n.status === "warn") ? "warn" : "ok"} />
      </div>
      <div className="pipeline">
        {nodes.map((node, index) => {
          const Icon = node.icon;
          return (
            <div className="pipeline-step" key={node.title}>
              <div className={`pipe-node pipe-${node.status}`}>
                <Icon size={20} />
              </div>
              <div className="pipe-text">
                <strong>{node.title}</strong>
                <span>{node.value}</span>
                <small>{node.detail}</small>
              </div>
              {index < nodes.length - 1 ? <ArrowRight className="pipe-arrow" size={18} /> : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function VolumeChart({ closing, selectedDate, calendar }) {
  const max = Math.max(...closing.map((row) => Math.max(row.totalOil || 0, row.totalGas || 0)), 1);
  const loaded = calendar?.summary?.loaded || closing.length;
  const total = calendar?.summary?.days || Math.max(loaded, 1);
  const ratio = Math.min(1, Math.max(0, loaded / total));
  const coverageTone = ratio < 0.2 ? "critical" : ratio < 0.6 ? "warn" : "ok";
  return (
    <section className="panel chart-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Produção medida</span>
          <h2>Fechamento diário</h2>
        </div>
        <span className="muted">Óleo m³ | Gás 10³ m³</span>
      </div>
      <div className="chart">
        {closing.map((row) => (
          <div className={`chart-day ${row.date === selectedDate ? "chart-active" : ""}`} key={row.date}>
            <div className="bars">
              <span className="bar oil" style={{ height: `${Math.max(6, (row.totalOil / max) * 100)}%` }} />
              <span className="bar gas" style={{ height: `${Math.max(6, (row.totalGas / max) * 100)}%` }} />
            </div>
            <strong>{shortDate(row.date)}</strong>
            <small>{row.status === "ok" ? "fechado" : "atenção"}</small>
          </div>
        ))}
      </div>
      <div className="legend">
        <span><i className="legend-oil" /> Óleo</span>
        <span><i className="legend-gas" /> Gás</span>
      </div>
      <div className="coverage-row">
        <span className={`coverage-label coverage-label-${coverageTone}`}>
          {loaded} de {total} dias carregados
        </span>
        <div className="coverage-bar">
          <div className={`coverage-fill coverage-fill-${coverageTone}`} style={{ width: `${ratio * 100}%` }} />
        </div>
      </div>
    </section>
  );
}

function ClosingTable({ rows, activeTag, setActiveTag, layers, onOpenDrawer }) {
  return (
    <section className="panel table-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Pontos de medição</span>
          <h2>Valores diários e fechamento</h2>
        </div>
        <span className="muted">{rows.length} registros</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Tag</th>
              <th>Família</th>
              {layers.raw ? <th>Raw</th> : null}
              {layers.xml ? <th>XML</th> : null}
              {layers.anp ? <th>Painel ANP</th> : null}
              <th>Delta XML/ANP</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const delta = row.anpCorrigido !== null && row.xmlCorrigido !== null ? row.anpCorrigido - row.xmlCorrigido : null;
              return (
                <tr
                  className={activeTag === row.tag ? "row-active" : ""}
                  key={`${row.date}-${row.family}-${row.tag}`}
                  onClick={() => {
                    setActiveTag(row.tag);
                    if (onOpenDrawer) onOpenDrawer(row.tag);
                    const target = document.getElementById("dossier-panel");
                    if (!target) return;
                    target.scrollIntoView({ behavior: "smooth", block: "center" });
                    target.classList.remove("panel-flash");
                    requestAnimationFrame(() => target.classList.add("panel-flash"));
                  }}
                >
                  <td><strong>{row.tag}</strong></td>
                  <td>{row.familyName}</td>
                  {layers.raw ? <td>{number(row.rawCorrigido, 4)}</td> : null}
                  {layers.xml ? <td>{number(row.xmlCorrigido, 4)}</td> : null}
                  {layers.anp ? <td>{number(row.anpCorrigido, 4)}</td> : null}
                  <td>{number(delta, 5)}</td>
                  <td><StatusPill status={row.status} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function TracePanel({ pointRows, activeTag }) {
  const selected = pointRows.find((row) => row.tag === activeTag) || pointRows[0];
  if (!selected) return null;
  const items = [
    ["Raw", selected.rawSource || "Sem arquivo CV direto", selected.rawOk ? "ok" : "warn"],
    ["XML", selected.xmlSource || "-", "ok"],
    ["ANP", selected.anpOk ? "Export Painel do Operador localizado" : "Não localizado", selected.anpOk ? "ok" : "critical"],
  ];
  return (
    <section className="panel trace-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Rastreio</span>
          <h2>{selected.tag}</h2>
        </div>
        <StatusPill status={selected.status} />
      </div>
      <div className="trace-list">
        {items.map(([title, detail, status], index) => (
          <div className="trace-item" key={title}>
            <div className={`trace-dot trace-${status}`}>{index + 1}</div>
            <div>
              <strong>{title}</strong>
              <span title={detail}>{detail}</span>
            </div>
          </div>
        ))}
      </div>
      <dl className="trace-metrics">
        <div>
          <dt>Raw corrigido</dt>
          <dd>{number(selected.rawCorrigido, 4)}</dd>
        </div>
        <div>
          <dt>XML corrigido</dt>
          <dd>{number(selected.xmlCorrigido, 4)}</dd>
        </div>
        <div>
          <dt>ANP recebido</dt>
          <dd>{number(selected.anpCorrigido, 4)}</dd>
        </div>
      </dl>
    </section>
  );
}

function AlertsPanel({ alerts }) {
  return (
    <section className="panel alerts-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Radar</span>
          <h2>Alertas e prazos</h2>
        </div>
        <Bell size={19} />
      </div>
      <div className="alerts-list">
        {alerts.map((alert, index) => (
          <article className={`alert alert-${alert.severity}`} key={`${alert.title}-${index}`}>
            <div>
              <strong>{alert.title}</strong>
              <span>{alert.detail}</span>
              <small>{alert.area} · {fullDate(alert.date)}</small>
            </div>
            <StatusPill status={alert.severity} />
          </article>
        ))}
      </div>
    </section>
  );
}

function SpecPanel({ latestPoints, bsw, latestAnpDate }) {
  const visible = latestPoints.slice(0, 10);
  return (
    <section className="panel spec-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Especificações</span>
          <h2>Limites e BSW</h2>
        </div>
        <Gauge size={19} />
      </div>
      <div className="spec-grid">
        <div className="spec-highlight">
          <span>Maior BSW observado</span>
          <strong>{number(bsw?.max?.bsw, 4)}%</strong>
          <small>{bsw?.max?.tag || "-"} em {fullDate(bsw?.max?.date)}</small>
        </div>
        <div className="spec-highlight">
          <span>Último Painel ANP</span>
          <strong>{fullDate(latestAnpDate)}</strong>
          <small>exportações recebidas na pasta</small>
        </div>
      </div>
      <div className="limit-list">
        {visible.map((point) => (
          <div className="limit-row" key={`${point.family}-${point.tag}`}>
            <div>
              <strong>{point.tag}</strong>
              <span>{point.fluid || point.familyName} · {point.meterType || "medidor"}</span>
            </div>
            <div>
              <small>máx op.</small>
              <b>{number(point.maxOperacao, 2)}</b>
            </div>
            <StatusPill status={point.inRange ? "ok" : "warn"} />
          </div>
        ))}
      </div>
    </section>
  );
}

function FailuresPanel({ failures, mpfm }) {
  const max = Math.max(...failures.byType.map((item) => item.value), 1);
  return (
    <section className="panel failures-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">NFSM e recon</span>
          <h2>Falhas abertas</h2>
        </div>
        <AlertTriangle size={19} />
      </div>
      <div className="failure-summary">
        <div>
          <span>Abertas</span>
          <strong>{failures.open}</strong>
        </div>
        <div>
          <span>Retornadas</span>
          <strong>{failures.returned}</strong>
        </div>
        <div>
          <span>Alertas MPFM</span>
          <strong>{mpfm.alerts.length}</strong>
        </div>
      </div>
      <div className="bar-list">
        {failures.byType.slice(0, 5).map((item) => (
          <div className="bar-row" key={item.name}>
            <span>{item.name}</span>
            <div><i style={{ width: `${(item.value / max) * 100}%` }} /></div>
            <b>{item.value}</b>
          </div>
        ))}
      </div>
      <div className="mpfm-status">
        {mpfm.status.slice(0, 6).map((item) => (
          <div key={item.date}>
            <span>{fullDate(item.date)}</span>
            <strong>{item.status}</strong>
            <small>{item.missingHours ? `faltam ${item.missingHours}` : "24h"}</small>
          </div>
        ))}
      </div>
    </section>
  );
}

function RangeBar({ label, item, unit }) {
  const lower = item?.lower;
  const upper = item?.upper;
  const value = item?.value;
  const hasRange = lower !== null && lower !== undefined && upper !== null && upper !== undefined && upper !== lower;
  const position = hasRange && value !== null && value !== undefined ? Math.max(0, Math.min(100, ((value - lower) / (upper - lower)) * 100)) : 50;
  return (
    <div className="range-row">
      <div className="range-label">
        <strong>{label}</strong>
        <span>{number(value, 3)} {unit}</span>
      </div>
      <div className={`range-track range-${item?.status || "warn"}`}>
        <i style={{ left: `${position}%` }} />
      </div>
      <div className="range-limits">
        <span>{number(lower, 2)}</span>
        <span>{number(upper, 2)}</span>
      </div>
    </div>
  );
}

function LimitEnvelopePanel({ monitors, activeTag }) {
  const selected = monitors.find((item) => item.tag === activeTag) || monitors[0];
  const critical = monitors.filter((item) => item.status === "critical").length;
  if (!selected) return null;
  return (
    <section className="panel envelope-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Faixas e PAM</span>
          <h2>Envelope do ponto {selected.tag}</h2>
        </div>
        <StatusPill status={selected.status} />
      </div>
      <div className="envelope-meta">
        <span>{selected.fluid || "-"} · {selected.meterType || "equipamento"}</span>
        <strong>{critical} pontos fora de faixa no último ANP</strong>
      </div>
      <RangeBar label="PAM / operação" item={selected.pam} unit="m³ ou 10³m³" />
      <RangeBar label="Pressão" item={selected.pressure} unit="kPa" />
      <RangeBar label="Temperatura" item={selected.temperature} unit="°C" />
      {selected.differential?.value !== null && selected.differential?.value !== undefined ? (
        <RangeBar label="Δ pressão" item={selected.differential} unit="kPa" />
      ) : null}
    </section>
  );
}

function UncertaintyPanel({ rows, selectedDate }) {
  const dateRows = rows.filter((row) => row.date === selectedDate);
  const max = Math.max(...dateRows.map((row) => row.uncertaintyMax || 0), 1);
  const withCadastro = dateRows.filter((row) => row.uncertaintyMax !== null && row.uncertaintyMax !== undefined).length;
  return (
    <section className="panel uncertainty-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Incerteza</span>
          <h2>Monitor diário do ponto</h2>
        </div>
        <span className="muted">{withCadastro}/{dateRows.length} com cadastro</span>
      </div>
      <div className="uncertainty-list">
        {dateRows.slice(0, 12).map((row) => (
          <div className="uncertainty-row" key={`${row.date}-${row.tag}`}>
            <span>{row.tag}</span>
            <div><i style={{ width: `${((row.uncertaintyMax || 0) / max) * 100}%` }} /></div>
            <b>{number(row.uncertaintyMax, 3)}%</b>
          </div>
        ))}
      </div>
      <p className="panel-note">Valor atual exibido é o limite cadastral. A fonte de cálculo diário fica pronta para certificados e memórias de incerteza.</p>
    </section>
  );
}

function AnalyticalPanel({ analytical }) {
  const rows = analytical?.labReport?.rows || [];
  const latest = analytical?.labReport?.latest || {};
  const recent = rows.slice(-6).reverse();
  return (
    <section className="panel analytical-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Físico-químico</span>
          <h2>Análises dos pontos fiscais e MPFM</h2>
        </div>
        <FlaskConical size={19} />
      </div>
      <div className="analysis-kpis">
        <div><span>Último BSW lab</span><strong>{number(latest.bsw, 3)}%</strong></div>
        <div><span>Densidade</span><strong>{number(latest.density, 2)}</strong></div>
        <div><span>API</span><strong>{number(latest.api, 2)}</strong></div>
      </div>
      <div className="analysis-list">
        {recent.map((row, index) => (
          <div key={`${row.date}-${row.labReport}-${index}`}>
            <strong>{fullDate(row.date)}</strong>
            <span>{row.labReport || "Lab report"} · BSW {number(row.bsw, 3)}% · dens. {number(row.density, 2)}</span>
          </div>
        ))}
      </div>
      <p className="panel-note">Fonte atual: {analytical?.labReport?.source || "não configurada"}.</p>
    </section>
  );
}

function MeasurementIntelligencePanel({ data, selectedDate }) {
  const insight = measurementInsights(data, selectedDate);
  const fiscal = insight.fiscalVsMultiphase;
  const oilDelta = diffValues(fiscal.oilFiscal, fiscal.oilRaw);
  const gasDelta = diffValues(fiscal.gasFiscal, fiscal.gasRaw);
  return (
    <section className="panel measurement-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Medição comparada</span>
          <h2>Fiscal x multifásico em {fullDate(selectedDate)}</h2>
        </div>
        <Gauge size={19} />
      </div>
      <div className="measurement-grid">
        <div>
          <span>Óleo fiscal / PI</span>
          <strong>{number(fiscal.oilFiscal, 3)}</strong>
          <small>raw/multifásico {number(fiscal.oilRaw, 3)} · Δ {number(oilDelta, 3)}</small>
        </div>
        <div>
          <span>Gás fiscal / PI</span>
          <strong>{number(fiscal.gasFiscal, 3)}</strong>
          <small>raw/multifásico {number(fiscal.gasRaw, 3)} · Δ {number(gasDelta, 3)}</small>
        </div>
      </div>
      <p className="panel-note">Amostras PI/AF usadas no dia: {number(fiscal.modelSamples, 0)}. Valores de CSV em alta frequência entram como média operacional; XML/Painel ANP seguem como fechamento fiscal.</p>
    </section>
  );
}

function GasBalancePanel({ data, selectedDate }) {
  const insight = measurementInsights(data, selectedDate);
  return (
    <section className="panel gas-balance-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Balanço de gás</span>
          <h2>Produção medida e pendências</h2>
        </div>
        <Activity size={19} />
      </div>
      <div className="balance-strip">
        <div><span>Fiscal/PI</span><strong>{number(insight.gasBalance.dayGas, 3)}</strong></div>
        <div><span>Injeção/controle</span><strong>{number(insight.gasBalance.injectionAverage, 3)}</strong></div>
        <div><span>Produção</span><strong>{number(insight.gasBalance.productionAverage, 3)}</strong></div>
        <div><span>Pendências</span><strong>{insight.gasBalance.pendingRows}</strong></div>
      </div>
      <p className="panel-note">Amostras de gás/modelos no dia: {number(insight.gasBalance.modelSamples, 0)}. O painel já reconhece fiscal, produção e injeção; cromatografia e flare podem entrar como fontes dedicadas quando houver export.</p>
    </section>
  );
}

function OffloadingPanel({ data, selectedDate }) {
  const insight = measurementInsights(data, selectedDate);
  return (
    <section className="panel offloading-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Offloading</span>
          <h2>Óleo fiscal como proxy até carregar fonte dedicada</h2>
        </div>
        <FileArchive size={19} />
      </div>
      <div className="balance-strip">
        <div><span>Dia</span><strong>{number(insight.offloading.dayOil, 3)}</strong></div>
        <div><span>Produção</span><strong>{number(insight.offloading.productionAverage, 3)}</strong></div>
        <div><span>Linhas fiscais</span><strong>{insight.offloading.fiscalRows}</strong></div>
      </div>
      <p className="panel-note">Fontes de óleo/modelos carregadas: {insight.offloading.sourceLoaded ? `${number(insight.offloading.modelSamples, 0)} amostras` : "ainda sem CSV dedicado"}. Para offloading fechado, falta somente uma fonte com volume transferido/tanque.</p>
    </section>
  );
}

function ProductionManagementPanel({ data, selectedDate }) {
  const insight = measurementInsights(data, selectedDate);
  const warning = insight.production.modelOutputTruncated
    ? `Atenção: ${insight.production.modelAggregatesPublished}/${insight.production.modelAggregatesTotal} agregados PI publicados no frontend.`
    : insight.production.modelWarnings[0];
  return (
    <section className="panel production-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Gestão de produção</span>
          <h2>Indicadores a partir das medições</h2>
        </div>
        <ClipboardCheck size={19} />
      </div>
      <div className="production-grid">
        <div><span>Arquivos</span><strong>{insight.production.files}</strong></div>
        <div><span>Comparações</span><strong>{insight.production.comparisons}</strong></div>
        <div><span>Linhas CSV</span><strong>{number(insight.production.modelRows, 0)}</strong></div>
        <div><span>Sinais PI</span><strong>{number(insight.production.modelSignals, 0)}</strong></div>
        <div><span>Alertas</span><strong>{insight.production.alerts}</strong></div>
        <div><span>Propostas</span><strong>{insight.production.proposals}</strong></div>
        <div><span>Dias carregados</span><strong>{insight.production.loadedDays}</strong></div>
        <div><span>Pendências</span><strong>{insight.production.openPendencies}</strong></div>
      </div>
      <p className="panel-note">Esses indicadores agora combinam XML/ANP, planilhas e os CSVs da pasta MODELOS; não dependem de banco externo.</p>
      {warning ? <p className="panel-note">{warning}</p> : null}
    </section>
  );
}

function GlobalAskPanel({ question, setQuestion, answer, askStatus, onAsk, aiConfig }) {
  const configured = Boolean(aiConfig?.enabled && aiConfig?.providers?.[aiConfig.activeProvider]?.apiKeySet);
  return (
    <section className="panel global-ask" aria-labelledby="global-ask-title">
      <div className="ask-heading">
        <BrainCircuit size={20} />
        <div>
          <span className="eyebrow">Pergunte ao Radar</span>
          <h2 id="global-ask-title">Perguntas sobre medições, lacunas e acessos às fontes</h2>
        </div>
        <StatusPill status={configured ? "ok" : "warn"} />
      </div>
      <form className="ask-box ask-box-live" onSubmit={onAsk}>
        <Search size={18} aria-hidden="true" />
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Pergunte: compare fiscal x multifásico, balanço de gás, offloading, pendências de maio/junho..."
          aria-label="Pergunta para o Radar ANP"
        />
        <button type="submit" disabled={askStatus.state === "busy" || !question.trim()}>
          <Send size={15} />
          <span>{askStatus.state === "busy" ? "consultando" : "perguntar"}</span>
        </button>
      </form>
      <div className="ask-answer" role="status" aria-live="polite">
        {askStatus.message ? <small>{askStatus.message}</small> : null}
        {answer ? <pre>{answer}</pre> : <p>O Radar responde com dados locais mesmo sem LLM; com a chave habilitada, usa o provedor configurado e registra a pergunta no log auditável.</p>}
      </div>
    </section>
  );
}

function AiRadarPanel({ ai, aiConfig }) {
  const safeAi = ai || { mode: "copiloto auditavel", principle: "Aguardando reprocessamento dos dados.", capabilities: [] };
  const configured = Boolean(aiConfig?.enabled && aiConfig?.providers?.[aiConfig.activeProvider]?.apiKeySet);
  return (
    <section className="panel ai-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">IA do Radar</span>
          <h2>Pergunte ao Radar e explique alertas</h2>
        </div>
        <BrainCircuit size={20} />
      </div>
      <div className="ai-ready-line">
        <StatusPill status={configured ? "ok" : "warn"} />
        <span>{configured ? "LLM habilitada; use o campo Pergunte ao Radar no topo." : "Resposta local ativa; salve e habilite uma chave para usar LLM."}</span>
      </div>
      <div className="ai-principle">
        <strong>{safeAi.mode}</strong>
        <span>{safeAi.principle}</span>
      </div>
      <div className="ai-capabilities">
        {safeAi.capabilities.map((item) => (
          <article key={item.name}>
            <FileSearch size={17} />
            <div>
              <strong>{item.name}</strong>
              <span>{item.detail}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function RegulatoryChecklistPanel({ config, matrix }) {
  const sourceMap = new Map((config.sources || []).map((source) => [source.id, source]));
  const items = [
    ["regulations", "Base normativa e manuais", "prazos, periodicidades e requisitos"],
    ["calibration", "Certificados e calibração", "validade, faixa calibrada e rastreabilidade"],
    ["uncertainty", "Incerteza do sistema", "memória de cálculo por ponto/malha"],
    ["physchem", "Análises físico-químicas", "óleo, gás, BSW, densidade, cromatografia"],
    ["samplingPlans", "Planos de coleta", "frequência, janela e evidência de execução"],
    ["equipmentDocs", "PAM e folhas de dados", "faixa de medição, limites e cadastro técnico"],
  ];
  return (
    <section className="panel checklist-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Checklist regulatório</span>
          <h2>Fontes exigidas e prontidão</h2>
        </div>
        <ClipboardCheck size={19} />
      </div>
      {matrix?.summary?.total ? (
        <div className="matrix-summary">
          <div>
            <span>Matriz SGM1</span>
            <strong>{matrix.summary.total}</strong>
            <small>requisitos RM</small>
          </div>
          {(matrix.summary.byCategory || []).map((item) => (
            <div key={item.name}>
              <span>{item.name}</span>
              <strong>{item.value}</strong>
              <small>itens</small>
            </div>
          ))}
        </div>
      ) : null}
      <div className="checklist-list">
        {items.map(([id, title, detail]) => {
          const source = sourceMap.get(id);
          const ready = Boolean(source?.paths?.length);
          return (
            <div className="checklist-row" key={id}>
              <StatusPill status={ready ? "ok" : "warn"} />
              <div>
                <strong>{title}</strong>
                <span>{detail}</span>
              </div>
              <small>{source?.paths?.length || 0} caminho(s)</small>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function DossierPanel({ activeTag, data }) {
  const monitor = (data.limitMonitors || []).find((item) => item.tag === activeTag);
  const pointRows = data.comparisons.filter((item) => item.tag === activeTag);
  const failures = (data.failures.latestOpen || []).filter((item) => item.tag === activeTag);
  const uncertainty = (data.uncertaintyMonitor || []).find((item) => item.tag === activeTag);
  if (!monitor && !pointRows.length) return null;
  return (
    <section className="panel dossier-panel" id="dossier-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Dossiê do ponto</span>
          <h2>{activeTag}</h2>
        </div>
        <Wrench size={19} />
      </div>
      <div className="dossier-grid">
        <div><span>Família</span><strong>{monitor?.familyName || pointRows[0]?.familyName || "-"}</strong></div>
        <div><span>Fluido</span><strong>{monitor?.fluid || "-"}</strong></div>
        <div><span>Medidor</span><strong>{monitor?.meterType || "-"}</strong></div>
        <div><span>Incerteza máx.</span><strong>{number(uncertainty?.uncertaintyMax, 3)}%</strong></div>
        <div><span>XML/ANP</span><strong>{pointRows.filter((row) => row.anpOk).length}/{pointRows.length}</strong></div>
        <div><span>NFSM aberta</span><strong>{failures.length}</strong></div>
      </div>
      <p className="panel-note">Este painel será o ponto de entrada para certificados, calibração, incerteza, análises, falhas, XMLs e evidência ANP.</p>
    </section>
  );
}

function PointDrawer({ tag, data, onClose }) {
  if (!tag) return null;
  const pointRows = data.comparisons.filter((item) => item.tag === tag);
  return (
    <>
      <div className="point-drawer-overlay" onClick={onClose} />
      <aside className="point-drawer">
        <div className="point-drawer-head">
          <div>
            <span className="eyebrow">Dossiê do ponto</span>
            <h2>{tag}</h2>
          </div>
          <button className="point-drawer-close" onClick={onClose} aria-label="Fechar dossiê">
            <X size={20} />
          </button>
        </div>
        <div className="point-drawer-body">
          <TracePanel pointRows={pointRows} activeTag={tag} />
          <DossierPanel activeTag={tag} data={data} />
          <LimitEnvelopePanel monitors={data.limitMonitors || []} activeTag={tag} />
        </div>
      </aside>
    </>
  );
}

function EventEvidencePanel({ radar }) {
  const summary = radar?.summary || {};
  const events = radar?.events || [];
  const visible = events.slice(0, 14);
  return (
    <section className="panel event-evidence-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Eventos x evidências</span>
          <h2>Alterações de parâmetros com prova documental</h2>
        </div>
        <FileSearch size={20} />
      </div>
      <div className="event-summary">
        <div><span>TXT varridos</span><strong>{summary.eventFilesScanned || 0}</strong></div>
        <div><span>Alterações</span><strong>{summary.parameterChanges || 0}</strong></div>
        <div><span>Evidências</span><strong>{summary.evidenceIndexed || 0}</strong></div>
        <div><span>Confirmadas</span><strong>{summary.confirmed || 0}</strong></div>
        <div><span>Apoio textual</span><strong>{summary.supporting || 0}</strong></div>
        <div><span>Sem prova</span><strong>{summary.critical || 0}</strong></div>
      </div>
      <div className="table-wrap event-table">
        <table>
          <thead>
            <tr>
              <th>Data</th>
              <th>Sistema</th>
              <th>Parâmetro</th>
              <th>Evidência esperada</th>
              <th>Melhor evidência</th>
              <th>Conteúdo</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((event, index) => {
              const best = event.evidenceCandidates?.[0];
              return (
                <tr key={`${event.timestamp}-${event.parameter}-${index}`}>
                  <td>{fullDateTime(event.timestamp)}</td>
                  <td>
                    <strong>{event.flowComputer || event.system || "-"}</strong>
                    <span>{event.tags?.join(", ") || "-"}</span>
                  </td>
                  <td>
                    <strong>{event.parameter}</strong>
                    <span>{event.oldValue}{" -> "}{event.newValue}</span>
                  </td>
                  <td>{event.expectedEvidenceLabels?.join(", ") || "-"}</td>
                  <td title={best?.path || "Nenhuma evidência candidata"}>
                    {best ? (
                      <>
                        <strong>{best.name}</strong>
                        <span>{best.contentReason || best.reasons?.join(", ") || `score ${best.score}`}</span>
                        {best.snippet ? <em>{best.snippet}</em> : null}
                      </>
                    ) : (
                      <span>Nenhuma evidência candidata</span>
                    )}
                  </td>
                  <td>
                    <strong className={`evidence-state evidence-${event.evidenceState || "missing"}`}>
                      {evidenceStateLabel[event.evidenceState] || event.evidenceState || "-"}
                    </strong>
                    <span>{best?.contentHits?.join(", ") || "-"}</span>
                  </td>
                  <td><StatusPill status={event.status} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="panel-note">
        Regra v2: alterações explícitas de parâmetro são cruzadas com documentos por tipo, data, tag/equipamento e conteúdo extraído.
      </p>
    </section>
  );
}

function DatabasePanel({ database }) {
  const counts = database?.tableCounts || {};
  const rows = Object.entries(counts);
  return (
    <section className="panel database-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Banco local</span>
          <h2>SQLite operacional</h2>
        </div>
        <Table2 size={20} />
      </div>
      <div className="database-summary">
        <div>
          <span>Arquivo</span>
          <strong>{database?.path ? "radar-anp.sqlite" : "não gerado"}</strong>
          <small>{database?.path || "rode Reprocessar dashboard"}</small>
        </div>
        <div>
          <span>Tabelas</span>
          <strong>{rows.length}</strong>
          <small>{number((database?.sizeBytes || 0) / 1024, 1)} KB</small>
        </div>
        <div>
          <span>Gerado</span>
          <strong>{database?.generatedAt?.replace("T", " ") || "-"}</strong>
          <small>sincronizado ao JSON</small>
        </div>
      </div>
      <div className="database-tables">
        {rows.map(([name, count]) => (
          <div key={name}>
            <span>{name}</span>
            <strong>{count}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function E2EView({ data, selectedDate, selectedRows, activeTag, setActiveTag, layers }) {
  return (
    <section className="view-stack">
      <div className="grid-main">
        <div className="primary-stack">
          <Pipeline selectedDate={selectedDate} rows={selectedRows} files={data.files} />
          <ClosingTable rows={selectedRows} activeTag={activeTag} setActiveTag={setActiveTag} layers={layers} />
        </div>
        <div className="right-stack">
          <DatabasePanel database={data.database} />
          <TracePanel pointRows={selectedRows} activeTag={activeTag} />
        </div>
      </div>
      <EventEvidencePanel radar={data.eventEvidenceRadar} />
    </section>
  );
}

function DeadlinesView({ data, selectedDate }) {
  const openFailures = data.failures?.latestOpen || [];
  const criticalAlerts = data.alerts.filter((alert) => alert.severity === "critical");
  const warnAlerts = data.alerts.filter((alert) => alert.severity === "warn");
  const matrixTotal = data.regulatoryMatrix?.summary?.total || 0;
  const sourceMap = new Map((data.config?.sources || []).map((source) => [source.id, source]));
  const deadlineCards = [
    ["Falhas abertas", data.failures?.open || 0, "NFSM em acompanhamento", "critical"],
    ["Alertas críticos", criticalAlerts.length, "prioridade de ação", criticalAlerts.length ? "critical" : "ok"],
    ["Alertas atenção", warnAlerts.length, "acompanhar evidência/prazo", warnAlerts.length ? "warn" : "ok"],
    ["Requisitos SGM", matrixTotal, "base normativa indexada", matrixTotal ? "ok" : "warn"],
  ];
  return (
    <section className="view-stack">
      <div className="deadline-grid">
        {deadlineCards.map(([title, value, detail, tone]) => (
          <article className={`kpi kpi-${tone}`} key={title}>
            <div className="kpi-icon"><Timer size={18} /></div>
            <div>
              <p>{title}</p>
              <strong>{value}</strong>
              <small>{detail}</small>
            </div>
          </article>
        ))}
      </div>
      <div className="grid-main">
        <section className="panel">
          <div className="panel-head">
            <div>
              <span className="eyebrow">Linha de prazo</span>
              <h2>Falhas e alertas regulatórios</h2>
            </div>
            <Bell size={20} />
          </div>
          <div className="deadline-list">
            {[...criticalAlerts, ...warnAlerts].slice(0, 16).map((alert, index) => (
              <article className={`deadline-row deadline-${alert.severity}`} key={`${alert.title}-${index}`}>
                <StatusPill status={alert.severity} />
                <div>
                  <strong>{alert.title}</strong>
                  <span>{alert.detail}</span>
                </div>
                <small>{alert.date ? fullDate(alert.date) : fullDate(selectedDate)}</small>
              </article>
            ))}
          </div>
        </section>
        <section className="panel">
          <div className="panel-head">
            <div>
              <span className="eyebrow">NFSM</span>
              <h2>Falhas abertas recentes</h2>
            </div>
            <AlertTriangle size={20} />
          </div>
          <div className="deadline-list">
            {openFailures.slice(0, 12).map((failure, index) => (
              <article className="deadline-row deadline-critical" key={`${failure.id || failure.tag}-${index}`}>
                <StatusPill status={failure.overdueDays && failure.overdueDays > 0 ? "critical" : "warn"} />
                <div>
                  <strong>{failure.id || failure.tag || "Falha"}</strong>
                  <span>{failure.tag || "-"} · {failure.type || failure.status || "em acompanhamento"}</span>
                </div>
                <small>{failure.forecastDate ? fullDate(failure.forecastDate) : "-"}</small>
              </article>
            ))}
          </div>
        </section>
      </div>
      <section className="panel">
        <div className="panel-head">
          <div>
            <span className="eyebrow">Checklist regulatório</span>
            <h2>Prontidão das fontes de obrigação</h2>
          </div>
          <ClipboardCheck size={20} />
        </div>
        <div className="source-readiness">
          {["regulations", "requirementsMatrix", "calibration", "uncertainty", "physchem", "samplingPlans", "equipmentDocs"].map((id) => {
            const source = sourceMap.get(id);
            const ready = Boolean(source?.paths?.length);
            return (
              <div key={id}>
                <StatusPill status={ready ? "ok" : "warn"} />
                <strong>{source?.label || id}</strong>
                <span>{source?.paths?.length || 0} caminho(s)</span>
              </div>
            );
          })}
        </div>
      </section>
    </section>
  );
}

const PROPOSALS_PAGE_SIZE = 10;

function ProposalsView({ data, onDecision, apiStatus }) {
  const proposals = data.changeProposals || [];
  const pending = proposals.filter((item) => item.status === "pending_authorization");
  const authorized = proposals.filter((item) => item.status === "authorized");
  const highRisk = proposals.filter((item) => item.risk === "alto");
  const confirmed = proposals.filter((item) => item.evidenceState === "confirmed");
  const cards = [
    ["Pendentes", pending.length, "aguardando autorização", pending.length ? "warn" : "ok"],
    ["Autorizadas", authorized.length, "registradas em trilha", authorized.length ? "ok" : "neutral"],
    ["Risco alto", highRisk.length, "exigem evidência forte", highRisk.length ? "critical" : "ok"],
    ["Evidência confirmada", confirmed.length, "texto ou valor encontrado", confirmed.length ? "ok" : "warn"],
  ];

  const [statusFilter, setStatusFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [page, setPage] = useState(1);

  const filteredProposals = proposals.filter((proposal) => {
    if (statusFilter !== "all" && proposal.status !== statusFilter) return false;
    if (riskFilter !== "all" && proposal.risk !== riskFilter) return false;
    return true;
  });
  const totalPages = Math.max(1, Math.ceil(filteredProposals.length / PROPOSALS_PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pagedProposals = filteredProposals.slice(
    (currentPage - 1) * PROPOSALS_PAGE_SIZE,
    currentPage * PROPOSALS_PAGE_SIZE
  );

  const handleStatusFilter = (value) => {
    setStatusFilter(value);
    setPage(1);
  };
  const handleRiskFilter = (value) => {
    setRiskFilter(value);
    setPage(1);
  };

  return (
    <section className="view-stack proposals-view">
      <div className="deadline-grid proposal-kpis">
        {cards.map(([title, value, detail, tone]) => (
          <article className={`kpi kpi-${tone}`} key={title}>
            <div className="kpi-icon"><ClipboardCheck size={18} /></div>
            <div>
              <p>{title}</p>
              <strong>{value}</strong>
              <small>{detail}</small>
            </div>
          </article>
        ))}
      </div>

      <section className="panel proposal-governance">
        <div className="panel-head">
          <div>
            <span className="eyebrow">Governança</span>
            <h2>Achado técnico vira proposta antes de alterar cadastro</h2>
          </div>
          <ShieldCheck size={20} />
        </div>
        <div className="approval-flow">
          {["arquivo fonte", "extração", "staging", "validação", "proposta", "autorização", "auditoria"].map((step, index) => (
            <div key={step}>
              <strong>{index + 1}</strong>
              <span>{step}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="panel proposal-inbox">
        <div className="panel-head">
          <div>
            <span className="eyebrow">Caixa de entrada</span>
            <h2>Propostas geradas dos documentos já analisados</h2>
          </div>
          <FileSearch size={20} />
        </div>
        <div className={`api-status api-${apiStatus.state}`}>
          <strong>{apiStatus.state === "busy" ? "Gravando" : apiStatus.state === "error" ? "Atenção" : "Auditoria"}</strong>
          <span>{apiStatus.message || "Autorizar registra a decisão; aplicação em cadastro mestre continua separada e rastreável."}</span>
        </div>
        <div className="proposal-filters">
          <label>
            Status
            <select value={statusFilter} onChange={(event) => handleStatusFilter(event.target.value)}>
              <option value="all">Todos</option>
              <option value="pending_authorization">Pendentes</option>
              <option value="authorized">Autorizadas</option>
              <option value="rejected">Rejeitadas</option>
              <option value="deferred">Adiadas</option>
            </select>
          </label>
          <label>
            Risco
            <select value={riskFilter} onChange={(event) => handleRiskFilter(event.target.value)}>
              <option value="all">Todos</option>
              <option value="alto">Alto</option>
              <option value="medio">Médio</option>
              <option value="baixo">Baixo</option>
            </select>
          </label>
          <span className="proposal-filter-count">
            {filteredProposals.length} de {proposals.length} propostas
          </span>
        </div>
        <div className="proposal-list">
          {pagedProposals.map((proposal) => (
            <article className={`proposal-card proposal-${proposal.risk}`} key={proposal.id}>
              <div className="proposal-main">
                <div className="proposal-titleline">
                  <StatusPill status={proposal.status} />
                  <strong>{proposal.title}</strong>
                </div>
                <div className="proposal-meta">
                  <span>{proposal.id}</span>
                  <span>{proposal.domain}</span>
                  <span>risco {proposal.risk}</span>
                  <span>confiança {proposal.confidence}</span>
                </div>
                <div className="proposal-values">
                  <div>
                    <span>valor atual</span>
                    <strong>{proposalValue(proposal.currentValue, proposal.unit)}</strong>
                  </div>
                  <ArrowRight size={18} />
                  <div>
                    <span>valor proposto</span>
                    <strong>{proposalValue(proposal.proposedValue, proposal.unit)}</strong>
                  </div>
                </div>
                <p>{proposal.evidenceText || "Sem trecho textual extraído; revisar fonte candidata."}</p>
                <small title={proposal.sourcePath || ""}>{proposal.sourceName || proposal.sourcePath || "fonte não informada"}</small>
              </div>
              <div className="proposal-actions">
                <StatusPill status={proposal.evidenceState || "missing"} />
                <button
                  className="primary"
                  disabled={apiStatus.state === "busy" || proposal.status === "authorized"}
                  onClick={() => onDecision(proposal.id, "authorized")}
                >
                  <ShieldCheck size={16} />
                  Autorizar
                </button>
                <button
                  disabled={apiStatus.state === "busy" || proposal.status === "rejected"}
                  onClick={() => onDecision(proposal.id, "rejected")}
                >
                  <AlertTriangle size={16} />
                  Rejeitar
                </button>
                <button
                  disabled={apiStatus.state === "busy" || proposal.status === "deferred"}
                  onClick={() => onDecision(proposal.id, "deferred")}
                >
                  <Timer size={16} />
                  Adiar
                </button>
              </div>
            </article>
          ))}
          {!proposals.length ? (
            <div className="empty-state">
              <FileSearch size={22} />
              <strong>Nenhuma proposta gerada</strong>
              <span>Reprocesse o dashboard após configurar fontes com documentos e planilhas.</span>
            </div>
          ) : null}
          {proposals.length && !filteredProposals.length ? (
            <div className="empty-state">
              <FileSearch size={22} />
              <strong>Nenhuma proposta com esse filtro</strong>
              <span>Ajuste status ou risco para ver outras propostas.</span>
            </div>
          ) : null}
        </div>
        {filteredProposals.length ? (
          <div className="proposal-pagination">
            <button disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}>
              Anterior
            </button>
            <span>
              Página {currentPage} de {totalPages}
            </span>
            <button disabled={currentPage >= totalPages} onClick={() => setPage(currentPage + 1)}>
              Próxima
            </button>
          </div>
        ) : null}
      </section>
    </section>
  );
}

function CalendarView({ data, onDecision, apiStatus }) {
  const calendar = data.operationalCalendar || { summary: {}, days: [] };
  const days = calendar.days || [];
  const [selectedDate, setSelectedDate] = useState(days.find((day) => day.openPendingCount)?.date || days.find((day) => day.loaded)?.date || days[0]?.date || "");
  const selected = days.find((day) => day.date === selectedDate) || days[0];
  const summary = calendar.summary || {};
  const cards = [
    ["Dias carregados", summary.loaded || 0, `${summary.days || 0} dias no calendário`, "ok"],
    ["Sem carga", summary.notLoaded || 0, "faltam arquivos/fonte", summary.notLoaded ? "critical" : "ok"],
    ["Atenção", summary.warn || 0, "dias com pendência", summary.warn ? "warn" : "ok"],
    ["Pendências abertas", summary.openPendencies || 0, "baixa ou correção", summary.openPendencies ? "critical" : "ok"],
  ];

  return (
    <section className="view-stack calendar-view">
      <div className="deadline-grid">
        {cards.map(([title, value, detail, tone]) => (
          <article className={`kpi kpi-${tone}`} key={title}>
            <div className="kpi-icon"><CalendarDays size={18} /></div>
            <div>
              <p>{title}</p>
              <strong>{value}</strong>
              <small>{detail}</small>
            </div>
          </article>
        ))}
      </div>

      <div className="grid-main">
        <section className="panel">
          <div className="panel-head">
            <div>
              <span className="eyebrow">Calendário</span>
              <h2>{calendar.month || "mês operacional"}</h2>
            </div>
            <CalendarDays size={20} />
          </div>
          <div className="calendar-grid">
            {days.map((day) => (
              <button
                className={`calendar-day calendar-${day.status} ${day.date === selected?.date ? "active" : ""}`}
                key={day.date}
                onClick={() => setSelectedDate(day.date)}
              >
                <strong>{day.day}</strong>
                <span>{day.loaded ? `${day.points} pts` : "sem carga"}</span>
                <i>{day.openPendingCount || 0}</i>
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <span className="eyebrow">Dia selecionado</span>
              <h2>{fullDate(selected?.date)}</h2>
            </div>
            <ClipboardCheck size={20} />
          </div>
          {selected ? (
            <div className="calendar-detail">
              <div className="calendar-facts">
                <div><span>Status</span><StatusPill status={selected.status} /></div>
                <div><span>XML</span><strong>{selected.xmlFamilies?.join(", ") || "-"}</strong></div>
                <div><span>Pacote</span><strong>{selected.packageFamilies?.join(", ") || "-"}</strong></div>
                <div><span>Pendências abertas</span><strong>{selected.openPendingCount}</strong></div>
              </div>
              <div className={`api-status api-${apiStatus.state}`}>
                <strong>{apiStatus.state === "busy" ? "Gravando" : apiStatus.state === "error" ? "Atenção" : "Baixa"}</strong>
                <span>{apiStatus.message || "Baixa operacional registra tratamento; correção definitiva vem da fonte e reprocessamento."}</span>
              </div>
              <div className="calendar-pendency-list">
                {(selected.pendingItems || []).map((item) => (
                  <article className={`calendar-pendency calendar-${item.severity}`} key={item.id}>
                    <div>
                      <StatusPill status={item.status || "open"} />
                      <strong>{item.title}</strong>
                      <span>{item.detail}</span>
                      <small>{item.recommendedAction}</small>
                    </div>
                    <div className="pendency-actions">
                      <button disabled={apiStatus.state === "busy" || item.status !== "open"} onClick={() => onDecision(item.id, "resolved")}>Baixar</button>
                      <button disabled={apiStatus.state === "busy" || item.status !== "open"} onClick={() => onDecision(item.id, "deferred")}>Adiar</button>
                      <button disabled={apiStatus.state === "busy" || item.status !== "open"} onClick={() => onDecision(item.id, "ignored")}>Ignorar</button>
                    </div>
                  </article>
                ))}
                {!selected.pendingItems?.length ? <div className="empty-state"><CheckCircle2 size={22} /><strong>Sem pendências neste dia</strong></div> : null}
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </section>
  );
}

function ConfigPanel({ data, config, setConfig, aiConfig, setAiConfig, onSave, onSaveAi, onRebuild, apiStatus, aiStatus }) {
  const updateSource = (sourceId, patch) => {
    setConfig((current) => ({
      ...current,
      sources: current.sources.map((source) => (source.id === sourceId ? { ...source, ...patch } : source)),
    }));
  };

  const updateAiConfig = (patch) => {
    setAiConfig((current) => ({ ...current, ...patch }));
  };

  const updateAiProvider = (providerId, patch) => {
    setAiConfig((current) => ({
      ...current,
      providers: {
        ...current.providers,
        [providerId]: {
          ...current.providers[providerId],
          ...patch,
        },
      },
    }));
  };

  const updateAiPermission = (permissionId, value) => {
    setAiConfig((current) => ({
      ...current,
      permissions: {
        ...current.permissions,
        [permissionId]: value,
      },
    }));
  };

  const sourceCount = config?.sources?.length || 0;
  const safeAiConfig = aiConfig || defaultAiConfig;
  const activeProvider = safeAiConfig.providers?.[safeAiConfig.activeProvider] || safeAiConfig.providers.openai;

  return (
    <section className="config-view">
      <div className="config-head panel">
        <div>
          <span className="eyebrow">Entrada de dados</span>
          <h2>Configuração das fontes do Radar ANP</h2>
          <p>
            Cada item aceita uma pasta ou arquivo. Quando for pasta, o processamento varre subpastas procurando os modelos já
            reconhecidos nesta base.
          </p>
        </div>
        <div className="config-actions">
          <button onClick={onSave} disabled={apiStatus.state === "busy"}>
            <ShieldCheck size={17} />
            Salvar caminhos
          </button>
          <button className="primary" onClick={onRebuild} disabled={apiStatus.state === "busy"}>
            <Activity size={17} />
            Reprocessar dashboard
          </button>
        </div>
      </div>

      <div className={`api-status api-${apiStatus.state}`}>
        <strong>{apiStatus.state === "busy" ? "Processando" : apiStatus.state === "error" ? "Atenção" : "Pronto"}</strong>
        <span>{apiStatus.message || `${sourceCount} grupos configurados em ${data.meta.configPath}`}</span>
      </div>

      <DatabasePanel database={data.database} />

      <section className="panel ai-config-panel">
        <div className="panel-head">
          <div>
            <span className="eyebrow">IA operacional</span>
            <h2>LLM, permissões e contexto do Radar</h2>
          </div>
          <BrainCircuit size={20} />
        </div>
        <div className="ai-config-layout">
          <form
            className="ai-provider-board"
            onSubmit={(event) => {
              event.preventDefault();
              onSaveAi();
            }}
          >
            <label className="switch-line ai-master-switch">
              <input
                type="checkbox"
                checked={Boolean(safeAiConfig.enabled)}
                onChange={(event) => updateAiConfig({ enabled: event.target.checked })}
              />
              <span>habilitar IA</span>
            </label>
            <div className="ai-provider-select">
              <label>
                <span>Provedor ativo</span>
                <select
                  value={safeAiConfig.activeProvider}
                  onChange={(event) => updateAiConfig({ activeProvider: event.target.value })}
                >
                  {Object.entries(safeAiConfig.providers).map(([id, provider]) => (
                    <option value={id} key={id}>{provider.label}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>Modelo</span>
                <select
                  value={activeProvider.model}
                  onChange={(event) => updateAiProvider(safeAiConfig.activeProvider, { model: event.target.value })}
                >
                  {(providerModels[safeAiConfig.activeProvider] || [activeProvider.model]).map((model) => (
                    <option value={model} key={model}>{model}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="llm-grid">
              {Object.entries(safeAiConfig.providers).map(([id, provider]) => (
                <article className={`llm-card ${safeAiConfig.activeProvider === id ? "llm-active" : ""}`} key={id}>
                  <div>
                    <strong>{provider.label}</strong>
                    <span>{provider.model}</span>
                  </div>
                  <label>
                    <span>{provider.apiKeySet ? "Chave cadastrada" : "Chave API"}</span>
                    <input
                      type="password"
                      value={provider.apiKey || ""}
                      placeholder={provider.apiKeySet ? "manter chave salva" : "cole a chave aqui"}
                      onChange={(event) => updateAiProvider(id, { apiKey: event.target.value })}
                      autoComplete="off"
                    />
                  </label>
                </article>
              ))}
            </div>
            <button className="primary ai-save" type="submit" disabled={aiStatus.state === "busy"}>
              <ShieldCheck size={17} />
              Salvar IA
            </button>
            <div className={`api-status api-${aiStatus.state}`}>
              <strong>{aiStatus.state === "busy" ? "Salvando" : aiStatus.state === "error" ? "Atenção" : "IA"}</strong>
              <span>{aiStatus.message || "Chaves ficam fora do dashboard-data.json e não são devolvidas ao navegador."}</span>
            </div>
          </form>

          <div className="ai-governance">
            <h3>Permissões com trilha</h3>
            {[
              ["readConfiguredFolders", "Ler pastas configuradas"],
              ["extractDocuments", "Extrair dados de documentos"],
              ["writeDrafts", "Gerar rascunhos/cadastros propostos"],
              ["copyMoveFiles", "Copiar ou mover arquivos"],
              ["requireApprovalForFileOps", "Exigir autorização para ação em arquivo"],
              ["auditLog", "Registrar ações em log auditável"],
            ].map(([id, label]) => (
              <label className="permission-row" key={id}>
                <input
                  type="checkbox"
                  checked={Boolean(safeAiConfig.permissions?.[id])}
                  onChange={(event) => updateAiPermission(id, event.target.checked)}
                />
                <span>{label}</span>
              </label>
            ))}
            <dl className="ai-paths">
              <div>
                <dt>Manifesto</dt>
                <dd>{safeAiConfig.contextManifestPath || "docs/ai-operational-context.md"}</dd>
              </div>
              <div>
                <dt>Log de ações</dt>
                <dd>{safeAiConfig.auditLogPath || "data/ai-action-log.jsonl"}</dd>
              </div>
            </dl>
          </div>
        </div>
      </section>

      <section className="panel interaction-map">
        <div className="panel-head">
          <div>
            <span className="eyebrow">Gráficos e telas</span>
            <h2>Áreas interativas do Radar</h2>
          </div>
          <Gauge size={20} />
        </div>
        <div className="interaction-grid">
          {graphAreas.map(([name, status, label, detail]) => (
            <article className={`interaction-card interaction-${status}`} key={name}>
              <strong>{name}</strong>
              <span>{label}</span>
              <p>{detail}</p>
            </article>
          ))}
        </div>
      </section>

      <div className="config-grid">
        {config.sources.map((source) => (
          <article className="config-card panel" key={source.id}>
            <div className="panel-head">
              <div>
                <span className="eyebrow">{source.id}</span>
                <h2>{source.label}</h2>
              </div>
              <label className="switch-line">
                <input
                  type="checkbox"
                  checked={Boolean(source.recursive)}
                  onChange={(event) => updateSource(source.id, { recursive: event.target.checked })}
                />
                <span>subpastas</span>
              </label>
            </div>
            <p>{source.description}</p>
            <label className="path-editor">
              <span>Caminhos</span>
              <textarea
                value={(source.paths || []).join("\n")}
                onChange={(event) =>
                  updateSource(source.id, {
                    paths: event.target.value
                      .split(/\r?\n/)
                      .map((value) => value.trim())
                      .filter(Boolean),
                  })
                }
                spellCheck="false"
              />
            </label>
            <small>Use um caminho por linha. Ex.: C:\Dados\ANP\Painel ou C:\Dados\ANP\Óleo Linear.xlsx</small>
          </article>
        ))}
      </div>
    </section>
  );
}

export function App() {
  const [data, setData] = useState(initialDashboardData);
  const [config, setConfig] = useState(initialDashboardData.config);
  const [aiConfig, setAiConfig] = useState(defaultAiConfig);
  const [activeView, setActiveView] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    const view = params.get("view");
    return ["config", "trilha", "prazos", "propostas", "calendario"].includes(view) ? view : "operacao";
  });
  const [apiStatus, setApiStatus] = useState({ state: "idle", message: "" });
  const [aiStatus, setAiStatus] = useState({ state: "idle", message: "" });
  const [askQuestion, setAskQuestion] = useState("Compare medição fiscal x multifásico e diga o que falta carregar.");
  const [askAnswer, setAskAnswer] = useState("");
  const [askStatus, setAskStatus] = useState({ state: "idle", message: "" });
  const dates = data.meta.sourceDates;
  const [selectedDate, setSelectedDate] = useState(dates[dates.length - 1]);
  const [activeTag, setActiveTag] = useState("20FT2303");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTag, setDrawerTag] = useState("");
  const [query, setQuery] = useState("");
  const [layers, setLayers] = useState({ raw: true, xml: true, anp: true });

  useEffect(() => {
    let cancelled = false;
    const loadLatestData = async () => {
      try {
        const response = await fetch("/api/data", { cache: "no-store" });
        if (!response.ok) return;
        const payload = await response.json();
        if (cancelled) return;
        setData(payload);
        setConfig(payload.config);
      } catch {
        // Static builds keep using the bundled JSON when the local data API is not available.
      }
    };

    loadLatestData();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadAiConfig = async () => {
      try {
        const response = await fetch("/api/ai-config", { cache: "no-store" });
        if (!response.ok) return;
        const payload = await response.json();
        if (!cancelled) setAiConfig(payload);
      } catch {
        setAiStatus({ state: "idle", message: "IA local ainda não configurada." });
      }
    };

    loadAiConfig();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!dates.includes(selectedDate)) {
      setSelectedDate(dates[dates.length - 1]);
    }
  }, [dates, selectedDate]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (activeView !== "operacao") {
      params.set("view", activeView);
    } else {
      params.delete("view");
    }
    const queryString = params.toString();
    window.history.replaceState({}, "", `${window.location.pathname}${queryString ? `?${queryString}` : ""}`);
  }, [activeView]);

  const saveConfig = async () => {
    setApiStatus({ state: "busy", message: "Salvando config/data-sources.json..." });
    try {
      const response = await fetch("/api/config", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(config),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Falha ao salvar configuração");
      setApiStatus({ state: "ok", message: `Configuração salva em ${payload.configPath}` });
      return true;
    } catch (error) {
      setApiStatus({
        state: "error",
        message: `Não consegui salvar via navegador. Rode o app com npm run app. Detalhe: ${error.message}`,
      });
      return false;
    }
  };

  const saveAiConfig = async () => {
    setAiStatus({ state: "busy", message: "Salvando config/ai-settings.local.json..." });
    try {
      const response = await fetch("/api/ai-config", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(aiConfig),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Falha ao salvar IA");
      setAiConfig(payload.config);
      setAiStatus({ state: "ok", message: `Configuração IA salva em ${payload.configPath}` });
      return true;
    } catch (error) {
      setAiStatus({
        state: "error",
        message: `Não consegui salvar a IA. Rode o app com npm run app. Detalhe: ${error.message}`,
      });
      return false;
    }
  };

  const rebuildDashboard = async () => {
    const saved = await saveConfig();
    if (!saved) return;
    setApiStatus({ state: "busy", message: "Reprocessando XMLs, TXTs e planilhas..." });
    try {
      const response = await fetch("/api/rebuild", { method: "POST" });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.stderr || payload.error || "Falha ao reprocessar");
      }
      setData(payload.data);
      setConfig(payload.data.config);
      setApiStatus({
        state: "ok",
        message: `Dashboard atualizado: ${payload.data.kpis.comparisonRows} comparações e ${payload.data.alerts.length} alertas.`,
      });
    } catch (error) {
      setApiStatus({ state: "error", message: error.message });
    }
  };

  const askRadar = async (event) => {
    event?.preventDefault();
    const questionText = askQuestion.trim();
    if (!questionText) return;
    setAskStatus({ state: "busy", message: "Consultando dados locais e IA configurada..." });
    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question: questionText, view: activeView, selectedDate, activeTag }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Falha ao perguntar ao Radar");
      setAskAnswer(payload.answer);
      setAskStatus({
        state: payload.providerError ? "warn" : "ok",
        message: payload.providerError ? `Resposta local gerada; provedor IA retornou: ${payload.providerError}` : `Resposta gerada por ${payload.provider}.`,
      });
    } catch (error) {
      setAskStatus({ state: "error", message: String(error.message || error) });
    }
  };

  const decideProposal = async (proposalId, decision) => {
    setApiStatus({ state: "busy", message: `Registrando decisão ${decision} para ${proposalId}...` });
    try {
      const response = await fetch("/api/proposals/decision", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ proposalId, decision, authorizedBy: "usuario" }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Falha ao registrar decisão");
      setData((current) => ({
        ...current,
        changeProposals: (current.changeProposals || []).map((proposal) =>
          proposal.id === proposalId ? payload.proposal : proposal
        ),
      }));
      setApiStatus({ state: "ok", message: `${proposalId} ${proposalStatusLabel[decision] || decision}; decisão gravada no log.` });
    } catch (error) {
      setApiStatus({ state: "error", message: String(error.message || error) });
    }
  };

  const decidePendency = async (pendencyId, decision) => {
    setApiStatus({ state: "busy", message: `Registrando baixa ${decision} para ${pendencyId}...` });
    try {
      const response = await fetch("/api/pendencies/decision", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ pendencyId, decision, closedBy: "usuario" }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Falha ao registrar baixa");
      setData((current) => ({
        ...current,
        operationalCalendar: {
          ...current.operationalCalendar,
          days: (current.operationalCalendar?.days || []).map((day) =>
            day.date === payload.day.date ? payload.day : day
          ),
        },
      }));
      setApiStatus({ state: "ok", message: `${pendencyId} registrado como ${statusLabel[decision] || decision}.` });
    } catch (error) {
      setApiStatus({ state: "error", message: String(error.message || error) });
    }
  };

  const selectedRows = useMemo(() => {
    return data.comparisons.filter((row) => {
      const matchesDate = row.date === selectedDate;
      const matchesQuery = !query || row.tag.toLowerCase().includes(query.toLowerCase()) || row.familyName.toLowerCase().includes(query.toLowerCase());
      return matchesDate && matchesQuery;
    });
  }, [data.comparisons, selectedDate, query]);

  const selectedClosing = data.closing.find((row) => row.date === selectedDate);
  const visibleAlerts = data.alerts.filter((alert) => !alert.date || alert.date === selectedDate || alert.severity === "critical");
  const rawOk = selectedRows.filter((row) => row.rawOk).length;
  const anpOk = selectedRows.filter((row) => row.anpOk).length;

  return (
    <div className="app-shell">
      <aside className="side-rail">
        <div className="brand">
          <ShieldCheck size={24} />
          <div>
            <strong>Radar ANP</strong>
            <span>Medição Bacalhau</span>
          </div>
        </div>
        <nav>
          <button className={activeView === "operacao" ? "active" : ""} onClick={() => setActiveView("operacao")}><Activity size={18} /> Operação</button>
          <button className={activeView === "config" ? "active" : ""} onClick={() => setActiveView("config")}><SlidersHorizontal size={18} /> Configuração</button>
          <button className={activeView === "trilha" ? "active" : ""} onClick={() => setActiveView("trilha")}><Layers3 size={18} /> Trilha E2E</button>
          <button className={activeView === "calendario" ? "active" : ""} onClick={() => setActiveView("calendario")}><CalendarDays size={18} /> Calendário</button>
          <button className={activeView === "prazos" ? "active" : ""} onClick={() => setActiveView("prazos")}><Timer size={18} /> Prazos</button>
          <button className={activeView === "propostas" ? "active" : ""} onClick={() => setActiveView("propostas")}><ClipboardCheck size={18} /> Propostas</button>
        </nav>
        <div className="rail-foot">
          <span>Gerado</span>
          <strong>{data.meta.generatedAt.replace("T", " ")}</strong>
        </div>
      </aside>

      <main>
        <header className={`topbar topbar-${activeView}`}>
          <div className="top-title">
            <div className="top-mark">
              <ShieldCheck size={22} />
              <span />
            </div>
            <div>
              <span className="eyebrow">{activeView === "config" ? "Entrada de dados" : activeView === "prazos" ? "Radar regulatório" : activeView === "trilha" ? "Rastreabilidade E2E" : activeView === "propostas" ? "Autorização auditável" : activeView === "calendario" ? "Carga diária" : "Dashboard operacional"}</span>
              <h1>{viewTitles[activeView] || viewTitles.operacao}</h1>
              <div className="top-meta">
                <span>Radar ANP</span>
                <span>{dates.length ? `${dates.length} dia(s) de medição` : "sem janela"}</span>
                <span>gerado {data.meta.generatedAt.replace("T", " ")}</span>
              </div>
            </div>
          </div>
          {["operacao", "trilha", "prazos"].includes(activeView) ? <div className="top-actions">
            <div className="searchbox">
              <Search size={17} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar tag ou família" />
            </div>
            <div className="date-switch">
              <CalendarDays size={17} />
              {dates.map((day) => (
                <button className={day === selectedDate ? "active" : ""} onClick={() => setSelectedDate(day)} key={day}>
                  {shortDate(day)}
                </button>
              ))}
            </div>
          </div> : null}
        </header>

        <GlobalAskPanel
          question={askQuestion}
          setQuestion={setAskQuestion}
          answer={askAnswer}
          askStatus={askStatus}
          onAsk={askRadar}
          aiConfig={aiConfig}
        />

        {drawerOpen && activeView === "operacao" ? (
          <PointDrawer
            tag={drawerTag}
            data={data}
            onClose={() => setDrawerOpen(false)}
          />
        ) : null}

        {activeView === "config" ? (
          <ConfigPanel
            data={data}
            config={config}
            setConfig={setConfig}
            aiConfig={aiConfig}
            setAiConfig={setAiConfig}
            onSave={saveConfig}
            onSaveAi={saveAiConfig}
            onRebuild={rebuildDashboard}
            apiStatus={apiStatus}
            aiStatus={aiStatus}
          />
        ) : activeView === "trilha" ? (
          <E2EView
            data={data}
            selectedDate={selectedDate}
            selectedRows={selectedRows}
            activeTag={activeTag}
            setActiveTag={setActiveTag}
            layers={layers}
          />
        ) : activeView === "prazos" ? (
          <DeadlinesView data={data} selectedDate={selectedDate} />
        ) : activeView === "propostas" ? (
          <ProposalsView data={data} onDecision={decideProposal} apiStatus={apiStatus} />
        ) : activeView === "calendario" ? (
          <CalendarView data={data} onDecision={decidePendency} apiStatus={apiStatus} />
        ) : (
        <>
        <section className="control-band">
          <div className="layer-toggles">
            {Object.entries({ raw: "Raw", xml: "XML", anp: "Painel ANP" }).map(([key, label]) => (
              <label key={key}>
                <input
                  type="checkbox"
                  checked={layers[key]}
                  onChange={() => setLayers((current) => ({ ...current, [key]: !current[key] }))}
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
          <div className="date-status">
            <StatusPill status={selectedClosing?.status || "warn"} />
            <span>{selectedClosing?.points || 0} pontos no fechamento</span>
            <ChevronRight size={16} />
          </div>
        </section>

        <OperatorPanelHealthPanel health={data.operatorPanelHealth} />

        <section className="kpi-grid">
          <Kpi icon={CheckCircle2} label="XML x ANP" value={`${anpOk}/${selectedRows.length}`} tone="ok" helper="recebido no Painel" />
          <Kpi icon={Database} label="Raw x XML" value={`${rawOk}/${selectedRows.length}`} tone={rawOk === selectedRows.length ? "ok" : "warn"} helper="fonte diária localizada" />
          <Kpi icon={Table2} label="Painel Operador" value={`${data.kpis.operatorPanelReady || 0}/${data.operatorPanelHealth?.required || 0}`} tone={data.operatorPanelHealth?.status === "ok" ? "ok" : "critical"} helper="fonte prioritária" />
          <Kpi icon={FileArchive} label="Famílias enviadas" value={`${new Set(data.files.filter((f) => f.date === selectedDate).map((f) => f.family)).size}/4`} tone="ok" helper="PMO PMGL PMGD PMAE" />
          <Kpi icon={AlertTriangle} label="Falhas abertas" value={data.failures.open} tone="critical" helper="NFSM em acompanhamento" />
          <Kpi icon={FileSearch} label="Eventos sem evidência" value={data.eventEvidenceRadar?.summary?.critical || 0} tone={(data.eventEvidenceRadar?.summary?.critical || 0) ? "critical" : "ok"} helper="alterações de parâmetro" />
        </section>

        <div className="grid-main">
          <div className="primary-stack">
            <Pipeline selectedDate={selectedDate} rows={selectedRows} files={data.files} />
            <ClosingTable
              rows={selectedRows}
              activeTag={activeTag}
              setActiveTag={setActiveTag}
              layers={layers}
              onOpenDrawer={(tag) => {
                setDrawerTag(tag);
                setDrawerOpen(true);
              }}
            />
          </div>
          <div className="right-stack">
            <TracePanel pointRows={selectedRows} activeTag={activeTag} />
            <AlertsPanel alerts={visibleAlerts} />
          </div>
        </div>

        <div className="grid-secondary">
          <VolumeChart closing={data.closing} selectedDate={selectedDate} calendar={data.operationalCalendar} />
          <MeasurementIntelligencePanel data={data} selectedDate={selectedDate} />
          <GasBalancePanel data={data} selectedDate={selectedDate} />
        </div>
        <div className="grid-tertiary">
          <OffloadingPanel data={data} selectedDate={selectedDate} />
          <ProductionManagementPanel data={data} selectedDate={selectedDate} />
          <SpecPanel latestPoints={data.latestPoints} bsw={data.bsw} latestAnpDate={data.meta.latestAnpDate} />
        </div>
        <div className="grid-tertiary">
          <FailuresPanel failures={data.failures} mpfm={data.mpfm} />
          <LimitEnvelopePanel monitors={data.limitMonitors || []} activeTag={activeTag} />
          <UncertaintyPanel rows={data.uncertaintyMonitor || []} selectedDate={selectedDate} />
        </div>
        <div className="grid-tertiary">
          <AnalyticalPanel analytical={data.analytical} />
          <DossierPanel activeTag={activeTag} data={data} />
          <RegulatoryChecklistPanel config={data.config} matrix={data.regulatoryMatrix} />
          <AiRadarPanel ai={data.ai} aiConfig={aiConfig} />
        </div>
        <EventEvidencePanel radar={data.eventEvidenceRadar} />
        </>
        )}
      </main>
    </div>
  );
}
