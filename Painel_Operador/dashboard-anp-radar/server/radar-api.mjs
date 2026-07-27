import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import { createReadStream } from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const serverDir = path.dirname(fileURLToPath(import.meta.url));
const appDir = path.resolve(serverDir, "..");
const configPath = path.join(appDir, "config", "data-sources.json");
const aiConfigPath = path.join(appDir, "config", "ai-settings.local.json");
const dataPath = path.join(appDir, "src", "data", "dashboard-data.json");
const sqlitePath = path.join(appDir, "data", "radar-anp.sqlite");
const proposalDecisionsPath = path.join(appDir, "data", "proposal-decisions.json");
const pendencyDecisionsPath = path.join(appDir, "data", "pendency-decisions.json");
const actionLogPath = path.join(appDir, "data", "ai-action-log.jsonl");
const distDir = path.join(appDir, "dist");
const host = process.env.RADAR_HOST || "127.0.0.1";
const port = Number(process.env.RADAR_PORT || 6287);
const maxBodyBytes = 1024 * 1024;
const pythonCommand = process.env.PYTHON_CMD || (process.platform === "win32" ? "python" : "python3");
const rebuildTimeoutMs = Number(process.env.RADAR_REBUILD_TIMEOUT_MS || 300000);
const llmTimeoutMs = Number(process.env.RADAR_LLM_TIMEOUT_MS || 30000);
const askRateWindowMs = Number(process.env.RADAR_ASK_RATE_WINDOW_MS || 60000);
const askRateLimit = Number(process.env.RADAR_ASK_RATE_LIMIT || 20);
const allowRemote = process.env.RADAR_ALLOW_REMOTE === "true";
const askRateBuckets = new Map();

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  process.stderr.write(`RADAR_PORT invalida: ${process.env.RADAR_PORT}. Use um numero entre 1 e 65535.\n`);
  process.exit(1);
}
if (!Number.isInteger(rebuildTimeoutMs) || rebuildTimeoutMs < 1000) {
  process.stderr.write(
    `RADAR_REBUILD_TIMEOUT_MS invalido: ${process.env.RADAR_REBUILD_TIMEOUT_MS}. Use um numero >= 1000.\n`,
  );
  process.exit(1);
}
if (!Number.isInteger(llmTimeoutMs) || llmTimeoutMs < 1000) {
  process.stderr.write(`RADAR_LLM_TIMEOUT_MS invalido: ${process.env.RADAR_LLM_TIMEOUT_MS}. Use um numero >= 1000.\n`);
  process.exit(1);
}
if (!Number.isInteger(askRateWindowMs) || askRateWindowMs < 1000 || !Number.isInteger(askRateLimit) || askRateLimit < 1) {
  process.stderr.write("RADAR_ASK_RATE_WINDOW_MS/RADAR_ASK_RATE_LIMIT invalidos. Use janela >= 1000 e limite >= 1.\n");
  process.exit(1);
}

const mimeTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".ico", "image/x-icon"],
  [".txt", "text/plain; charset=utf-8"],
]);

const defaultAiConfig = {
  schemaVersion: 1,
  enabled: false,
  activeProvider: "openai",
  providers: {
    openai: {
      label: "OpenAI",
      model: "gpt-4.1",
      apiKey: "",
      apiKeySet: false,
    },
    anthropic: {
      label: "Claude",
      model: "claude-3-5-sonnet-latest",
      apiKey: "",
      apiKeySet: false,
    },
    google: {
      label: "Gemini",
      model: "gemini-1.5-pro",
      apiKey: "",
      apiKeySet: false,
    },
  },
  permissions: {
    readConfiguredFolders: true,
    extractDocuments: true,
    writeDrafts: true,
    copyMoveFiles: false,
    requireApprovalForFileOps: true,
    auditLog: true,
  },
  contextManifestPath: path.join(appDir, "docs", "ai-operational-context.md"),
  auditLogPath: path.join(appDir, "data", "ai-action-log.jsonl"),
};

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    let size = 0;
    req.on("data", (chunk) => {
      size += chunk.length;
      if (size > maxBodyBytes) {
        reject(new Error("Payload muito grande"));
        req.destroy();
        return;
      }
      body += chunk;
    });
    req.on("end", () => resolve(body));
    req.on("error", reject);
  });
}

function sendJson(res, status, payload) {
  res.statusCode = status;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.end(JSON.stringify(payload));
}

function sanitizeErrorMessage(error) {
  const message = String(error?.message || error || "Erro interno");
  return message
    .replace(/[A-Z]:\\Users\\[^\\]+/gi, "C:\\Users\\[usuario]")
    .replace(/\/home\/[^/]+/gi, "/home/[usuario]")
    .replace(/\\\\[^\\]+\\[^\\\s]+/g, "\\\\[servidor]\\[compartilhamento]");
}

function sanitizeProviderMessage(error) {
  const message = sanitizeErrorMessage(error);
  return message
    .replace(/sk-[A-Za-z0-9_\-*]+/g, "[api-key]")
    .replace(/key provided:[\s\S]*?api-keys\.?/i, "key provided: [api-key].");
}

function sendApiError(res, error) {
  const code = error?.statusCode || (error?.message === "Payload muito grande" ? 413 : 500);
  sendJson(res, code, { ok: false, error: sanitizeErrorMessage(error) });
}

function createBadRequest(message) {
  const error = new Error(message);
  error.statusCode = 400;
  return error;
}

function createApiError(statusCode, message) {
  const error = new Error(message);
  error.statusCode = statusCode;
  return error;
}

function isLocalAddress(value) {
  const address = String(value || "").replace(/^::ffff:/, "");
  return address === "127.0.0.1" || address === "::1" || address === "::";
}

function assertLocalRequest(req) {
  if (allowRemote) return;
  if (!isLocalAddress(req.socket.remoteAddress)) {
    throw createApiError(403, "Acesso remoto bloqueado. Use RADAR_ALLOW_REMOTE=true apenas em ambiente protegido.");
  }
}

function normalizeQuestion(value) {
  return String(value || "").replace(/[\u0000-\u001f\u007f]+/g, " ").replace(/\s+/g, " ").trim();
}

function enforceAskRateLimit(req) {
  const now = Date.now();
  const key = req.socket.remoteAddress || "local";
  const bucket = askRateBuckets.get(key);
  if (!bucket || now - bucket.startedAt >= askRateWindowMs) {
    askRateBuckets.set(key, { startedAt: now, count: 1 });
    return;
  }
  if (bucket.count >= askRateLimit) {
    throw createApiError(429, `Limite de perguntas excedido. Tente novamente em ${Math.ceil((askRateWindowMs - (now - bucket.startedAt)) / 1000)}s.`);
  }
  bucket.count += 1;
}

function assertPlainObject(value, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw createBadRequest(`${label} deve ser um objeto`);
  }
}

function hasUnsafePathSegment(value) {
  return String(value)
    .split(/[\\/]+/)
    .some((segment) => segment === "..");
}

function isWithinDirectory(candidate, directory) {
  const relative = path.relative(directory, candidate);
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

async function validateConfiguredPath(rawPath, workspaceRoot, expectedKind, sourceId) {
  if (typeof rawPath !== "string" || !rawPath.trim()) {
    throw createBadRequest(`Caminho vazio em ${sourceId}`);
  }
  if (rawPath.includes("\0") || hasUnsafePathSegment(rawPath)) {
    throw createBadRequest(`Caminho invalido em ${sourceId}: ${rawPath}`);
  }

  const resolved = path.resolve(path.isAbsolute(rawPath) ? rawPath : path.join(workspaceRoot, rawPath));
  let stats;
  let realResolved;
  try {
    realResolved = await fs.realpath(resolved);
    if (!isWithinDirectory(realResolved, workspaceRoot)) {
      throw createBadRequest(`Caminho fora da pasta raiz em ${sourceId}: ${resolved}`);
    }
    stats = await fs.stat(realResolved);
  } catch (error) {
    if (error.statusCode) throw error;
    throw createBadRequest(`Caminho nao encontrado em ${sourceId}: ${resolved}`);
  }

  if (expectedKind === "folder" && !stats.isDirectory()) {
      throw createBadRequest(`Fonte ${sourceId} deve apontar para uma pasta: ${realResolved}`);
  }
  if (expectedKind === "file" && !stats.isFile()) {
    throw createBadRequest(`Fonte ${sourceId} deve apontar para um arquivo: ${realResolved}`);
  }
}

async function validateDataSourcesConfig(config) {
  assertPlainObject(config, "Configuracao");
  if (config.schemaVersion !== 1) {
    throw createBadRequest("schemaVersion invalida");
  }
  if (typeof config.workspaceRoot !== "string" || !config.workspaceRoot.trim()) {
    throw createBadRequest("workspaceRoot obrigatorio");
  }
  if (config.workspaceRoot.includes("\0") || hasUnsafePathSegment(config.workspaceRoot)) {
    throw createBadRequest(`workspaceRoot invalido: ${config.workspaceRoot}`);
  }

  const configuredWorkspaceRoot = path.resolve(config.workspaceRoot);
  let workspaceRoot;
  try {
    workspaceRoot = await fs.realpath(configuredWorkspaceRoot);
    const stats = await fs.stat(workspaceRoot);
    if (!stats.isDirectory()) {
      throw createBadRequest(`workspaceRoot deve apontar para uma pasta: ${workspaceRoot}`);
    }
  } catch (error) {
    if (error.statusCode) throw error;
    throw createBadRequest(`workspaceRoot nao encontrado: ${configuredWorkspaceRoot}`);
  }

  if (!Array.isArray(config.sources)) {
    throw createBadRequest("sources deve ser uma lista");
  }

  for (const source of config.sources) {
    assertPlainObject(source, "Fonte");
    if (typeof source.id !== "string" || !source.id.trim()) {
      throw createBadRequest("Fonte sem id");
    }
    if (!new Set(["folder", "file"]).has(source.kind)) {
      throw createBadRequest(`Fonte ${source.id} tem kind invalido`);
    }
    if (!Array.isArray(source.paths) || source.paths.length === 0) {
      throw createBadRequest(`Fonte ${source.id} deve ter ao menos um caminho`);
    }
    for (const rawPath of source.paths) {
      await validateConfiguredPath(rawPath, workspaceRoot, source.kind, source.id);
    }
  }
}

function isAllowedOrigin(req) {
  const origin = req.headers.origin;
  if (!origin) return true;
  const allowed = new Set([
    `http://${host}:${port}`,
    `http://localhost:${port}`,
    `http://127.0.0.1:${port}`,
  ]);
  return allowed.has(origin);
}

function createProviderFailure(providerId, response) {
  const providerLabel = providerId === "openai" ? "OpenAI" : providerId === "anthropic" ? "Anthropic" : "Google";
  if (response.status === 401 || response.status === 403) {
    return new Error(`${providerLabel} recusou a chave ou permissao configurada.`);
  }
  if (response.status === 429) {
    return new Error(`${providerLabel} atingiu limite de uso ou cota.`);
  }
  if (response.status >= 500) {
    return new Error(`${providerLabel} esta indisponivel no momento.`);
  }
  return new Error(`${providerLabel} retornou falha HTTP ${response.status}.`);
}

async function fetchWithTimeout(url, options) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), llmTimeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error(`Tempo limite de ${Math.round(llmTimeoutMs / 1000)}s excedido na chamada IA.`);
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

async function readJsonFile(filePath, fallback) {
  try {
    const raw = await fs.readFile(filePath, "utf-8");
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function mergeAiConfig(value = {}) {
  const merged = {
    ...defaultAiConfig,
    ...value,
    providers: {
      ...defaultAiConfig.providers,
      ...(value.providers || {}),
    },
    permissions: {
      ...defaultAiConfig.permissions,
      ...(value.permissions || {}),
    },
  };

  for (const provider of Object.keys(defaultAiConfig.providers)) {
    merged.providers[provider] = {
      ...defaultAiConfig.providers[provider],
      ...(value.providers?.[provider] || {}),
    };
    merged.providers[provider].apiKeySet = Boolean(merged.providers[provider].apiKey);
  }

  return merged;
}

function redactAiConfig(value) {
  const copy = mergeAiConfig(value);
  for (const provider of Object.keys(copy.providers)) {
    copy.providers[provider] = {
      ...copy.providers[provider],
      apiKey: "",
      apiKeySet: Boolean(value?.providers?.[provider]?.apiKey),
    };
  }
  return copy;
}

async function readAiConfig() {
  try {
    const raw = await fs.readFile(aiConfigPath, "utf-8");
    return mergeAiConfig(JSON.parse(raw));
  } catch {
    return mergeAiConfig();
  }
}

function summarizeMeasurementData(data) {
  const comparisons = Array.isArray(data.comparisons) ? data.comparisons : [];
  const closing = Array.isArray(data.closing) ? data.closing : [];
  const mpfmStatus = Array.isArray(data.mpfm?.status) ? data.mpfm.status : [];
  const mpfmAlerts = Array.isArray(data.mpfm?.alerts) ? data.mpfm.alerts : [];
  const gasRows = comparisons.filter((row) => row.fluid === "Gas" || /gas/i.test(row.familyName || ""));
  const fiscalGas = gasRows.reduce((total, row) => total + (Number(row.anpCorrigido ?? row.xmlCorrigido) || 0), 0);
  const rawGas = gasRows.reduce((total, row) => total + (Number(row.rawCorrigido) || 0), 0);
  const oilRows = comparisons.filter((row) => row.fluid === "Oleo" || /oleo|óleo/i.test(row.familyName || ""));
  const fiscalOil = oilRows.reduce((total, row) => total + (Number(row.anpCorrigido ?? row.xmlCorrigido) || 0), 0);
  const rawOil = oilRows.reduce((total, row) => total + (Number(row.rawCorrigido) || 0), 0);
  const loadedDates = data.meta?.sourceDates || [];
  const calendar = data.operationalCalendar?.summary || {};
  return {
    generatedAt: data.meta?.generatedAt,
    loadedDates,
    fiscalVsMultiphase: {
      fiscalOil,
      rawOil,
      oilDelta: fiscalOil - rawOil,
      fiscalGas,
      rawGas,
      gasDelta: fiscalGas - rawGas,
      mpfmStatus: mpfmStatus.slice(0, 8),
      mpfmAlerts: mpfmAlerts.slice(0, 8),
    },
    gasBalance: {
      measuredGas: closing.reduce((total, row) => total + (Number(row.totalGas) || 0), 0),
      gasMeasurementPoints: gasRows.length,
      pendingGasRows: gasRows.filter((row) => !row.rawOk || !row.anpOk).length,
    },
    offloading: {
      measuredOil: closing.reduce((total, row) => total + (Number(row.totalOil) || 0), 0),
      fiscalOilRows: oilRows.length,
      missingOffloadingSource: true,
      note: "Nao ha arquivo de offloading nomeado/identificado na base atual; o Radar usa medicao fiscal de oleo como proxy operacional ate a pasta correta ser indicada.",
    },
    productionManagement: {
      comparisons: comparisons.length,
      files: Array.isArray(data.files) ? data.files.length : 0,
      alerts: Array.isArray(data.alerts) ? data.alerts.length : 0,
      proposals: Array.isArray(data.changeProposals) ? data.changeProposals.length : 0,
      calendar,
    },
    alertsTop: (Array.isArray(data.alerts) ? data.alerts : [])
      .slice(0, 20)
      .map((a) => ({ severity: a.severity, date: a.date, title: a.title, detail: a.detail, area: a.area })),
    failures: {
      total: data.failures?.total ?? 0,
      open: data.failures?.open ?? 0,
      returned: data.failures?.returned ?? 0,
      byType: data.failures?.byType ?? [],
    },
    proposalsByStatus: groupBy(Array.isArray(data.changeProposals) ? data.changeProposals : [], "status"),
    proposalsHighRiskTop: (Array.isArray(data.changeProposals) ? data.changeProposals : [])
      .filter((p) => p.risk === "alto" && p.status === "pending_authorization")
      .slice(0, 15)
      .map((p) => ({ title: p.title, targetId: p.targetId, field: p.field, currentValue: p.currentValue, proposedValue: p.proposedValue, confidence: p.confidence })),
    latestPointsByTag: (Array.isArray(data.latestPoints) ? data.latestPoints : []).map((p) => ({
      tag: p.tag,
      family: p.familyName,
      fluid: p.fluid,
      date: p.date,
      inRange: p.inRange,
      volumeCorrigido: p.volumeCorrigido,
    })),
    regulatoryMatrixCount: Array.isArray(data.regulatoryMatrix) ? data.regulatoryMatrix.length : 0,
    eventEvidenceCount: Array.isArray(data.eventEvidenceRadar?.events) ? data.eventEvidenceRadar.events.length : 0,
    databaseTables: data.database?.tables || [],
    sources: (data.config?.sources || []).map((s) => ({ id: s.id, kind: s.kind, paths: s.paths })),
  };
}

function groupBy(rows, field) {
  const counts = {};
  for (const row of rows) {
    const key = row?.[field] ?? "desconhecido";
    counts[key] = (counts[key] || 0) + 1;
  }
  return counts;
}

function buildLocalRadarAnswer(question, data) {
  const summary = summarizeMeasurementData(data);
  const missingRanges = [];
  const days = data.operationalCalendar?.days || [];
  for (const day of days.filter((item) => !item.loaded)) {
    const previous = missingRanges[missingRanges.length - 1];
    if (previous) {
      const next = new Date(`${previous.end}T00:00:00Z`);
      next.setUTCDate(next.getUTCDate() + 1);
      if (next.toISOString().slice(0, 10) === day.date) {
        previous.end = day.date;
        previous.count += 1;
        continue;
      }
    }
    missingRanges.push({ start: day.date, end: day.date, count: 1 });
  }
  return [
    `Pergunta: ${question}`,
    `Base atual: ${summary.generatedAt}; dias carregados: ${(summary.loadedDates || []).join(", ") || "nenhum"}.`,
    `Fiscal x multifasico: oleo fiscal ${summary.fiscalVsMultiphase.fiscalOil.toFixed(3)} vs raw/multifasico ${summary.fiscalVsMultiphase.rawOil.toFixed(3)}; gas fiscal ${summary.fiscalVsMultiphase.fiscalGas.toFixed(3)} vs raw/multifasico ${summary.fiscalVsMultiphase.rawGas.toFixed(3)}.`,
    `Balanco de gas: ${summary.gasBalance.measuredGas.toFixed(3)} em fechamento, ${summary.gasBalance.gasMeasurementPoints} linhas de gas, ${summary.gasBalance.pendingGasRows} pendencia(s) em gas.`,
    `Offloading: a pasta atual ainda nao trouxe fonte de offloading identificada; o painel usa oleo medido fiscal como proxy ate voce indicar a pasta/arquivo correto.`,
    `Gestao de producao: ${summary.productionManagement.comparisons} comparacoes, ${summary.productionManagement.files} arquivos, ${summary.productionManagement.alerts} alertas, ${summary.productionManagement.proposals} propostas.`,
    `Calendario: ${summary.productionManagement.calendar.days || 0} dias, ${summary.productionManagement.calendar.loaded || 0} carregados, ${summary.productionManagement.calendar.notLoaded || 0} sem carga, ${summary.productionManagement.calendar.openPendencies || 0} pendencias abertas.`,
    `Faltantes: ${missingRanges.map((range) => `${range.start} a ${range.end} (${range.count})`).join("; ") || "sem lacunas"}.`,
  ].join("\n");
}

async function readManifest() {
  try {
    return await fs.readFile(defaultAiConfig.contextManifestPath, "utf-8");
  } catch {
    return "";
  }
}

async function buildAiPrompt(question, data) {
  const manifest = await readManifest();
  return [
    "Voce e o consultor do Radar ANP de medicao fiscal e operacional. Responda em portugues, de forma objetiva. Use o manifesto operacional para entender fontes, tabelas, telas e regras, e o contexto JSON para os numeros e registros atuais. Se a informacao nao existir, diga qual pasta/fonte precisa ser indicada.",
    `Manifesto operacional:\n${manifest}`,
    `Pergunta do usuario: ${question}`,
    `Contexto: ${JSON.stringify(summarizeMeasurementData(data))}`,
  ].join("\n\n");
}

async function callAiProvider(config, prompt) {
  const providerId = config.activeProvider || "openai";
  const provider = config.providers?.[providerId];
  if (!config.enabled) throw createBadRequest("IA desabilitada nas configuracoes");
  if (!provider) throw createBadRequest(`Provedor IA nao encontrado: ${providerId}`);
  if (!provider?.apiKey) throw createBadRequest(`Chave API nao cadastrada para ${provider?.label || providerId}`);

  if (providerId === "anthropic") {
    const response = await fetchWithTimeout("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": provider.apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({ model: provider.model, max_tokens: 900, messages: [{ role: "user", content: prompt }] }),
    });
    const payload = await response.json();
    if (!response.ok) throw createProviderFailure(providerId, response);
    return payload.content?.map((item) => item.text).filter(Boolean).join("\n") || "Sem resposta textual.";
  }

  if (providerId === "google") {
    const response = await fetchWithTimeout(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(provider.model)}:generateContent?key=${encodeURIComponent(provider.apiKey)}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
    });
    const payload = await response.json();
    if (!response.ok) throw createProviderFailure(providerId, response);
    return payload.candidates?.[0]?.content?.parts?.map((item) => item.text).filter(Boolean).join("\n") || "Sem resposta textual.";
  }

  const response = await fetchWithTimeout("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${provider.apiKey}`,
    },
    body: JSON.stringify({ model: provider.model, input: prompt }),
  });
  const payload = await response.json();
  if (!response.ok) throw createProviderFailure(providerId, response);
  return payload.output_text || payload.output?.flatMap((item) => item.content || []).map((item) => item.text).filter(Boolean).join("\n") || "Sem resposta textual.";
}

function applyProposalDecision(data, record) {
  const proposals = Array.isArray(data.changeProposals) ? data.changeProposals : [];
  const proposal = proposals.find((item) => item.id === record.proposalId);
  if (!proposal) {
    return null;
  }
  proposal.status = record.decision;
  proposal.authorizedBy = record.authorizedBy;
  proposal.authorizedAt = record.authorizedAt;
  proposal.decisionNote = record.note;
  proposal.auditTrail = Array.isArray(proposal.auditTrail) ? proposal.auditTrail : [];
  proposal.auditTrail.push({
    at: record.authorizedAt,
    actor: record.authorizedBy,
    action: record.decision,
    note: record.note,
    source: "api/proposals/decision",
  });
  return proposal;
}

function applyPendencyDecision(data, record) {
  const days = Array.isArray(data.operationalCalendar?.days) ? data.operationalCalendar.days : [];
  for (const day of days) {
    const items = Array.isArray(day.pendingItems) ? day.pendingItems : [];
    const item = items.find((candidate) => candidate.id === record.pendencyId);
    if (!item) continue;
    item.status = record.decision;
    item.closedBy = record.closedBy;
    item.closedAt = record.closedAt;
    item.decisionNote = record.note;
    day.openPendingCount = items.filter((candidate) => candidate.status === "open").length;
    day.resolvedPendingCount = items.length - day.openPendingCount;
    if (day.openPendingCount === 0 && items.length) {
      day.status = "resolved";
    }
    return { day, item };
  }
  return null;
}

function runDataBuild() {
  return new Promise((resolve) => {
    let finished = false;
    const child = spawn(pythonCommand, [path.join(appDir, "scripts", "build_dashboard_data.py")], {
      cwd: appDir,
      shell: false,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      if (finished) return;
      finished = true;
      child.kill();
      resolve({ code: -1, stdout, stderr: `${stderr}\nTimeout: reprocessamento excedeu ${rebuildTimeoutMs}ms`.trim() });
    }, rebuildTimeoutMs);
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("close", (code) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      resolve({ code, stdout, stderr });
    });
    child.on("error", (error) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      resolve({ code: -1, stdout, stderr: sanitizeErrorMessage(error) });
    });
  });
}

async function handleApi(req, res, url) {
  try {
    if (req.method === "GET" && url.pathname === "/api/config") {
      const raw = await fs.readFile(configPath, "utf-8");
      sendJson(res, 200, JSON.parse(raw));
      return;
    }

    if (req.method === "POST" && url.pathname === "/api/config") {
      const body = await readBody(req);
      const parsed = JSON.parse(body);
      await validateDataSourcesConfig(parsed);
      await fs.mkdir(path.dirname(configPath), { recursive: true });
      await fs.writeFile(configPath, JSON.stringify(parsed, null, 2), "utf-8");
      sendJson(res, 200, { ok: true, configPath });
      return;
    }

    if (req.method === "GET" && url.pathname === "/api/data") {
      const raw = await fs.readFile(dataPath, "utf-8");
      sendJson(res, 200, JSON.parse(raw));
      return;
    }

    if (req.method === "POST" && url.pathname === "/api/proposals/decision") {
      const body = await readBody(req);
      const parsed = JSON.parse(body);
      const allowed = new Set(["authorized", "rejected", "deferred"]);
      if (!parsed.proposalId || !allowed.has(parsed.decision)) {
        sendJson(res, 400, { ok: false, error: "proposalId e decision valida sao obrigatorios" });
        return;
      }

      const now = new Date().toISOString();
      const record = {
        proposalId: parsed.proposalId,
        decision: parsed.decision,
        note: parsed.note || "",
        authorizedBy: parsed.authorizedBy || "usuario",
        authorizedAt: now,
      };

      const data = await readJsonFile(dataPath, {});
      const proposal = applyProposalDecision(data, record);
      if (!proposal) {
        sendJson(res, 404, { ok: false, error: "Proposta nao encontrada" });
        return;
      }

      const decisions = await readJsonFile(proposalDecisionsPath, { schemaVersion: 1, decisions: {} });
      decisions.schemaVersion = 1;
      decisions.decisions = decisions.decisions || {};
      decisions.decisions[record.proposalId] = record;
      await fs.mkdir(path.dirname(proposalDecisionsPath), { recursive: true });
      await fs.writeFile(proposalDecisionsPath, JSON.stringify(decisions, null, 2), "utf-8");
      await fs.writeFile(dataPath, JSON.stringify(data, null, 2), "utf-8");

      const auditLine = {
        at: now,
        actor: record.authorizedBy,
        action: "proposal_decision",
        proposalId: record.proposalId,
        decision: record.decision,
        note: record.note,
      };
      await fs.mkdir(path.dirname(actionLogPath), { recursive: true });
      await fs.appendFile(actionLogPath, `${JSON.stringify(auditLine)}\n`, "utf-8");

      sendJson(res, 200, { ok: true, proposal, decisionsPath: proposalDecisionsPath, auditLogPath: actionLogPath });
      return;
    }

    if (req.method === "POST" && url.pathname === "/api/pendencies/decision") {
      const body = await readBody(req);
      const parsed = JSON.parse(body);
      const allowed = new Set(["resolved", "deferred", "ignored"]);
      if (!parsed.pendencyId || !allowed.has(parsed.decision)) {
        sendJson(res, 400, { ok: false, error: "pendencyId e decision valida sao obrigatorios" });
        return;
      }

      const now = new Date().toISOString();
      const record = {
        pendencyId: parsed.pendencyId,
        decision: parsed.decision,
        note: parsed.note || "",
        closedBy: parsed.closedBy || "usuario",
        closedAt: now,
      };

      const data = await readJsonFile(dataPath, {});
      const result = applyPendencyDecision(data, record);
      if (!result) {
        sendJson(res, 404, { ok: false, error: "Pendencia nao encontrada" });
        return;
      }

      const decisions = await readJsonFile(pendencyDecisionsPath, { schemaVersion: 1, decisions: {} });
      decisions.schemaVersion = 1;
      decisions.decisions = decisions.decisions || {};
      decisions.decisions[record.pendencyId] = record;
      await fs.mkdir(path.dirname(pendencyDecisionsPath), { recursive: true });
      await fs.writeFile(pendencyDecisionsPath, JSON.stringify(decisions, null, 2), "utf-8");
      await fs.writeFile(dataPath, JSON.stringify(data, null, 2), "utf-8");

      const auditLine = {
        at: now,
        actor: record.closedBy,
        action: "pendency_decision",
        pendencyId: record.pendencyId,
        decision: record.decision,
        note: record.note,
      };
      await fs.mkdir(path.dirname(actionLogPath), { recursive: true });
      await fs.appendFile(actionLogPath, `${JSON.stringify(auditLine)}\n`, "utf-8");

      sendJson(res, 200, { ok: true, day: result.day, pendency: result.item, decisionsPath: pendencyDecisionsPath, auditLogPath: actionLogPath });
      return;
    }

    if (req.method === "GET" && url.pathname === "/api/database-summary") {
      const raw = await fs.readFile(dataPath, "utf-8");
      const parsed = JSON.parse(raw);
      let stat = null;
      try {
        stat = await fs.stat(sqlitePath);
      } catch {
        stat = null;
      }
      sendJson(res, 200, {
        ok: Boolean(stat),
        path: sqlitePath,
        sizeBytes: stat?.size || 0,
        generatedAt: parsed.database?.generatedAt || null,
        tables: parsed.database?.tables || [],
        tableCounts: parsed.database?.tableCounts || {},
      });
      return;
    }

    if (req.method === "GET" && url.pathname === "/api/ai-config") {
      const aiConfig = await readAiConfig();
      sendJson(res, 200, redactAiConfig(aiConfig));
      return;
    }

    if (req.method === "POST" && url.pathname === "/api/ai-config") {
      const body = await readBody(req);
      const incoming = mergeAiConfig(JSON.parse(body));
      const current = await readAiConfig();
      const persisted = mergeAiConfig(incoming);
      for (const provider of Object.keys(persisted.providers)) {
        if (!persisted.providers[provider].apiKey) {
          persisted.providers[provider].apiKey = current.providers?.[provider]?.apiKey || "";
        }
        persisted.providers[provider].apiKeySet = Boolean(persisted.providers[provider].apiKey);
      }
      await fs.mkdir(path.dirname(aiConfigPath), { recursive: true });
      await fs.writeFile(aiConfigPath, JSON.stringify(persisted, null, 2), "utf-8");
      sendJson(res, 200, { ok: true, configPath: aiConfigPath, config: redactAiConfig(persisted) });
      return;
    }

    if (req.method === "POST" && url.pathname === "/api/ask") {
      enforceAskRateLimit(req);
      const body = await readBody(req);
      const parsed = JSON.parse(body || "{}");
      const question = normalizeQuestion(parsed.question);
      if (!question) {
        throw createBadRequest("Pergunta obrigatoria");
      }
      if (question.length > 1000) {
        throw createBadRequest("Pergunta muito longa. Use ate 1000 caracteres.");
      }
      const data = JSON.parse(await fs.readFile(dataPath, "utf-8"));
      const aiConfig = await readAiConfig();
      const localAnswer = buildLocalRadarAnswer(question, data);
      let answer = localAnswer;
      let provider = "radar-local";
      let providerError = null;
      if (aiConfig.enabled && aiConfig.providers?.[aiConfig.activeProvider]?.apiKey) {
        try {
          answer = await callAiProvider(aiConfig, await buildAiPrompt(question, data));
          provider = aiConfig.activeProvider;
        } catch (error) {
          providerError = sanitizeProviderMessage(error);
        }
      }
      const auditLine = {
        timestamp: new Date().toISOString(),
        type: "ai_question",
        provider,
        providerError,
        question,
      };
      await fs.mkdir(path.dirname(actionLogPath), { recursive: true });
      await fs.appendFile(actionLogPath, `${JSON.stringify(auditLine)}\n`, "utf-8");
      sendJson(res, 200, { ok: true, answer, provider, providerError, summary: summarizeMeasurementData(data) });
      return;
    }

    if (req.method === "POST" && url.pathname === "/api/rebuild") {
      const result = await runDataBuild();
      if (result.code !== 0) {
        sendJson(res, 500, { ok: false, ...result });
        return;
      }
      const raw = await fs.readFile(dataPath, "utf-8");
      sendJson(res, 200, { ok: true, ...result, data: JSON.parse(raw) });
      return;
    }

    sendJson(res, 404, { ok: false, error: "Endpoint nao encontrado" });
  } catch (error) {
    sendApiError(res, error);
  }
}

async function sendStaticFile(res, filePath) {
  const stat = await fs.stat(filePath);
  if (!stat.isFile()) {
    res.statusCode = 404;
    res.end("Not found");
    return;
  }

  res.statusCode = 200;
  res.setHeader("content-type", mimeTypes.get(path.extname(filePath).toLowerCase()) || "application/octet-stream");
  res.setHeader("content-length", stat.size);
  createReadStream(filePath).pipe(res);
}

async function handleStatic(req, res, url) {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.statusCode = 405;
    res.end("Method not allowed");
    return;
  }

  let decodedPath = "";
  try {
    decodedPath = decodeURIComponent(url.pathname);
  } catch {
    res.statusCode = 400;
    res.end("Bad request");
    return;
  }

  if (decodedPath.includes("\0")) {
    res.statusCode = 400;
    res.end("Bad request");
    return;
  }

  const requestedPath = decodedPath === "/" ? "index.html" : decodedPath.replace(/^\/+/, "");
  const candidatePath = path.resolve(distDir, requestedPath);
  if (!isWithinDirectory(candidatePath, distDir)) {
    res.statusCode = 403;
    res.end("Forbidden");
    return;
  }

  try {
    await sendStaticFile(res, candidatePath);
  } catch {
    await sendStaticFile(res, path.join(distDir, "index.html"));
  }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || "/", `http://${host}:${port}`);
  try {
    assertLocalRequest(req);
    if (!isAllowedOrigin(req)) {
      sendJson(res, 403, { ok: false, error: "Origem nao autorizada" });
      return;
    }

    if (req.method === "OPTIONS") {
      res.statusCode = 204;
      res.end();
      return;
    }

    if (url.pathname.startsWith("/api/")) {
      await handleApi(req, res, url);
      return;
    }
    await handleStatic(req, res, url);
  } catch (error) {
    sendApiError(res, error);
  }
});

server.on("error", (error) => {
  if (error?.code === "EADDRINUSE") {
    process.stderr.write(`Porta ${host}:${port} ja esta em uso. Feche o processo atual ou rode com RADAR_PORT=6291.\n`);
    process.exit(1);
  }
  throw error;
});

server.listen(port, host, () => {
  process.stdout.write(`Radar ANP rodando em http://${host}:${port}\n`);
});
