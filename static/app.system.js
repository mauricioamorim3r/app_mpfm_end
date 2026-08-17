'use strict';

// ── OUTPUTS ───────────────────────────────────────────────────────────────────
async function loadOutputs() {
  const d = await j(`${API}/list-outputs`);
  const files = d.files || [];
  const host = document.getElementById('outputsContext');
  if (host) {
    const latest = files[0] || null;
    const totalKb = files.reduce((acc, f) => acc + Number(f.size_kb || 0), 0);
    const rebuilding = files.filter(f => f.is_rebuilding);
    const months = [...new Set(files.map(f => {
      const m = String(f.name || '').match(/_(JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)_([0-9]{4})/i);
      return m ? `${m[1].toUpperCase()}/${m[2]}` : '';
    }).filter(Boolean))];
    host.innerHTML = `
      <div class="outputs-context-card"><div class="k">Arquivos</div><div class="v">${files.length}</div><div class="m">planilhas prontas para consulta e download</div></div>
      <div class="outputs-context-card"><div class="k">Último gerado</div><div class="v">${latest ? escapeHtml(latest.modified) : '—'}</div><div class="m" title="${escapeHtml(latest?.name || '')}">${escapeHtml(latest?.name || 'Nenhum arquivo ainda')}</div></div>
      <div class="outputs-context-card"><div class="k">Volume total</div><div class="v">${new Intl.NumberFormat('pt-BR', {maximumFractionDigits:1}).format(totalKb)} KB</div><div class="m">soma aproximada dos arquivos exibidos</div></div>
      <div class="outputs-context-card"><div class="k">Meses cobertos</div><div class="v">${months.length || 0}</div><div class="m">${months.join(', ') || 'Sem identificação mensal no nome'}</div></div>
      ${rebuilding.length ? `<div class="muted" style="grid-column:1 / -1; padding-top:4px" aria-live="polite">⏳ ${rebuilding.length} workbook(s) em atualização assíncrona. Aguarde alguns segundos antes de baixar.</div>` : ''}
    `;
  }
  document.getElementById('outputRows').innerHTML = (d.files||[]).map(f =>
    `<tr><td>${escapeHtml(f.name)}</td><td>${escapeHtml(f.size_kb)} KB</td><td>${escapeHtml(f.modified)}</td>
     <td>${f.is_rebuilding
       ? `<button class="btn secondary sm" type="button" disabled aria-disabled="true" aria-label="Workbook em atualização assíncrona" title="${escapeHtml(f.rebuild_message || 'Workbook em atualização assíncrona')}">⏳ Em atualização</button>`
       : `<a class="btn secondary sm" style="text-decoration:none" href="${API}/download/${encodeURIComponent(f.name)}">↓ Baixar</a>`}</td></tr>`
  ).join('') || '<tr><td colspan="4" class="muted">Nenhum Excel gerado.</td></tr>';
}

// ── SETTINGS MODAL ────────────────────────────────────────────────────────────
function fillSummaryConversionSettings() {
  const current = ((state.prefs || {}).summary_conversions) || {};
  const gasInputUnit = String(current.gas_input_unit || 'Sm³').replace(/^sm³$/i, 'Sm³');
  document.getElementById('cfgOilM3ToBbl').value = current.oil_m3_to_bbl_factor ?? 6.28981;
  document.getElementById('cfgGasInputUnit').value = gasInputUnit;
  document.getElementById('cfgGasSm3PerBoe').value = current.gas_sm3_per_boe_factor ?? 170;
  document.getElementById('cfgGasBoeMode').value = current.gas_boe_mode || 'Padrão corporativo';
  document.getElementById('cfgShowBoeCriterion').checked = current.show_boe_criterion !== false;
  document.getElementById('summaryConversionStatus').textContent = '';
}

function systemEscapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function getEquationReferenceSnapshot() {
  const prefs = ((state.prefs || {}).summary_conversions) || {};
  const oilFactor = Number(document.getElementById('cfgOilM3ToBbl')?.value || prefs.oil_m3_to_bbl_factor || 6.28981);
  const gasUnit = document.getElementById('cfgGasInputUnit')?.value || prefs.gas_input_unit || 'Sm³';
  const gasFactor = Number(document.getElementById('cfgGasSm3PerBoe')?.value || prefs.gas_sm3_per_boe_factor || 170);
  const gasMode = document.getElementById('cfgGasBoeMode')?.value || prefs.gas_boe_mode || 'Padrão corporativo';
  return {
    oilFactor,
    gasUnit,
    gasFactor,
    gasMode,
    generatedAt: new Date().toLocaleString('pt-BR'),
  };
}

function openEquationReferencePrintView() {
  const status = document.getElementById('equationGuideStatus');
  const snapshot = getEquationReferenceSnapshot();
  const reportWindow = window.open('', '_blank', 'noopener,noreferrer');
  if (!reportWindow) {
    if (status) status.textContent = 'Não foi possível abrir a janela de impressão.';
    return;
  }
  if (status) status.textContent = 'Página imprimível aberta em nova aba.';
  const equations = [
    {
      title: 'Desvio diário MPFM × Separador',
      formula: '((MPFM / Separador) - 1) × 100',
      detail: 'Usado nos gráficos mensais quando o modo selecionado é MPFM × Separador.',
    },
    {
      title: 'Desvio diário Subsea × Topside',
      formula: '((Subsea / Topside) - 1) × 100',
      detail: 'Usado no monitoramento e no modo Subsea × Topside. Topside é a referência operacional da razão.',
    },
    {
      title: 'Desvio acumulado do mês',
      formula: '((Σ Subsea / Σ Topside) - 1) × 100',
      detail: 'Aplicado após somar o mês inteiro. Não usamos média simples dos percentuais diários.',
    },
    {
      title: 'Conversão óleo → bbl',
      formula: `bbl = m³ × ${snapshot.oilFactor}`,
      detail: 'Fator atual de conversão configurado pela aplicação.',
    },
    {
      title: 'Conversão gás → BOE',
      formula: `BOE gás = ${snapshot.gasUnit} / ${snapshot.gasFactor}`,
      detail: `Modo atual: ${snapshot.gasMode}. O fator pode ser alterado em Configurações.`,
    },
  ];
  reportWindow.document.write(`<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Equações e critérios da aplicação</title>
  <style>
    :root{color-scheme:light;font-family:Segoe UI,Arial,sans-serif}
    *{box-sizing:border-box}
    body{margin:0;background:#f5f7fa;color:#102033}
    .page{max-width:980px;margin:0 auto;padding:32px 28px 44px}
    .toolbar{display:flex;gap:10px;justify-content:flex-end;margin-bottom:18px}
    .btn{border:1px solid #c8d4e3;background:#fff;color:#102033;border-radius:10px;padding:10px 14px;font:600 13px Segoe UI,Arial,sans-serif;cursor:pointer}
    .hero{background:linear-gradient(135deg,#0f2740,#163a5d);color:#fff;border-radius:18px;padding:24px 24px 20px;box-shadow:0 20px 50px rgba(16,32,51,.16)}
    .hero h1{margin:0 0 10px;font-size:28px;line-height:1.15}
    .hero p{margin:0;font-size:14px;line-height:1.6;color:rgba(255,255,255,.84)}
    .meta{margin-top:14px;font-size:12px;color:rgba(255,255,255,.72)}
    .section{margin-top:22px}
    .section h2{margin:0 0 12px;font-size:18px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
    .card{background:#fff;border:1px solid #dbe4ee;border-radius:16px;padding:16px 18px;box-shadow:0 10px 24px rgba(16,32,51,.06)}
    .card h3{margin:0 0 8px;font-size:14px;color:#102033}
    .formula{font:700 14px Consolas,'IBM Plex Mono',monospace;color:#0d5ea8;line-height:1.5;word-break:break-word}
    .detail{margin-top:8px;font-size:12px;color:#536579;line-height:1.55}
    .criteria{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}
    .criteria .card strong{display:block;font-size:22px;margin-bottom:6px}
    .criteria .card span{font-size:12px;color:#536579;line-height:1.5}
    .notes{margin-top:18px;background:#fff;border:1px solid #dbe4ee;border-radius:16px;padding:16px 18px}
    .notes ul{margin:10px 0 0 18px;padding:0}
    .notes li{margin:0 0 8px;font-size:12px;line-height:1.55;color:#33465b}
    @media print{
      body{background:#fff}
      .page{max-width:none;padding:0}
      .toolbar{display:none}
      .hero,.card,.notes{box-shadow:none}
    }
  </style>
</head>
<body>
  <div class="page">
    <div class="toolbar">
      <button class="btn" onclick="window.print()">Imprimir</button>
      <button class="btn" onclick="window.close()">Fechar</button>
    </div>
    <section class="hero">
      <h1>Equações e critérios da aplicação</h1>
      <p>Referência operacional para leitura dos gráficos, do monitoramento de pares e das conversões exibidas no resumo. Esta página replica as fórmulas mostradas em Configurações em um formato pronto para impressão.</p>
      <div class="meta">Gerado em ${systemEscapeHtml(snapshot.generatedAt)}</div>
    </section>
    <section class="section">
      <h2>Fórmulas principais</h2>
      <div class="grid">
        ${equations.map((item) => `
          <article class="card">
            <h3>${systemEscapeHtml(item.title)}</h3>
            <div class="formula">${systemEscapeHtml(item.formula)}</div>
            <div class="detail">${systemEscapeHtml(item.detail)}</div>
          </article>
        `).join('')}
      </div>
    </section>
    <section class="section">
      <h2>Critérios atuais</h2>
      <div class="criteria">
        <article class="card"><strong>HC ±10%</strong><span>Faixa atual de aceitação para desvio de hidrocarbonetos no monitoramento Subsea × Topside.</span></article>
        <article class="card"><strong>Total ±7%</strong><span>Faixa atual de aceitação para desvio total no monitoramento Subsea × Topside.</span></article>
        <article class="card"><strong>8 dias</strong><span>Limiar de atenção para dias consecutivos fora do limite.</span></article>
        <article class="card"><strong>10 dias</strong><span>Gatilho operacional para início do protocolo SGM-FM.</span></article>
      </div>
    </section>
    <section class="notes">
      <strong>Leituras importantes</strong>
      <ul>
        <li>No monitoramento de pares, o valor mostrado como referência é sempre o Topside. O percentual reflete quanto o Subsea ficou acima ou abaixo do Topside.</li>
        <li>O acumulado do mês é calculado com os somatórios mensais antes da razão. Isso evita distorção por média simples de percentuais diários.</li>
        <li>As conversões de BOE dependem do fator configurado pela operação e devem ser interpretadas junto com a unidade base do gás.</li>
      </ul>
    </section>
  </div>
</body>
</html>`);
  reportWindow.document.close();
}

function fillThemeModeSettings() {
  const mode = normalizeThemeMode((state.prefs || {}).theme_mode);
  const select = document.getElementById('cfgThemeMode');
  if (select) select.value = mode;
  if (typeof syncThemeControls === 'function') syncThemeControls(mode);
  const status = document.getElementById('themeModeStatus');
  if (status) status.textContent = '';
}

function getRecoveryMonth() {
  return document.getElementById('recoveryTargetMonth')?.value || document.getElementById('globalMonth')?.value || '';
}

function getRecoveryDate() {
  const raw = document.getElementById('recoveryTargetDate')?.value || '';
  if (!raw) return '';
  if (typeof parseBrDateToIso === 'function') {
    return parseBrDateToIso(raw) || raw;
  }
  return raw;
}

function getRecoveryBaseUnicaFile() {
  return document.getElementById('recoveryBaseUnicaFile')?.files?.[0] || null;
}

function getRecoveryBackupZipFile() {
  return document.getElementById('recoveryBackupZipFile')?.files?.[0] || null;
}

function formatMonitorTimestamp(value) {
  const raw = String(value || '').trim();
  if (!raw) return '—';
  const dt = new Date(raw);
  if (!Number.isNaN(dt.getTime())) {
    const pad = n => String(n).padStart(2, '0');
    return `${pad(dt.getDate())}/${pad(dt.getMonth() + 1)}/${dt.getFullYear()} ${pad(dt.getHours())}:${pad(dt.getMinutes())}:${pad(dt.getSeconds())}`;
  }
  return raw.replace('T', ' ').slice(0, 19);
}

function fillRecoverySettings() {
  const month = document.getElementById('globalMonth')?.value || '';
  const input = document.getElementById('recoveryTargetMonth');
  if (input && month) input.value = month;
  const log = document.getElementById('recoveryLog');
  if (log) log.textContent = 'Nenhuma ação executada ainda.';
  bindRecoveryControlSync();
  syncRecoveryControls();
}

function setRecoveryLog(message) {
  const log = document.getElementById('recoveryLog');
  if (log) log.textContent = message;
}

function isRecoveryDangerAcknowledged() {
  return !!document.getElementById('recoveryDangerAck')?.checked;
}

function setRecoveryButtonDisabled(id, disabled) {
  const button = document.getElementById(id);
  if (!button || button.dataset.busy === '1') return;
  button.disabled = !!disabled;
}

function syncRecoveryControls() {
  const hasMonth = !!String(getRecoveryMonth() || '').trim();
  ['btnRecoveryDiagnostics', 'btnRecoverySyncSepMonth', 'btnRecoveryRecomputeMonth', 'btnRecoveryRebuildMonth', 'btnRecoverySanitizeImports']
    .forEach(id => setRecoveryButtonDisabled(id, !hasMonth));
  const dangerOk = isRecoveryDangerAcknowledged();
  setRecoveryButtonDisabled('btnRecoveryDeleteDay', !(dangerOk && !!getRecoveryDate()));
  setRecoveryButtonDisabled('btnRecoveryApplyBaseUnica', !(dangerOk && !!getRecoveryBaseUnicaFile()));
  setRecoveryButtonDisabled('btnRecoveryRestoreBackupZip', !(dangerOk && !!getRecoveryBackupZipFile()));
  ['btnDownloadBackupClear', 'btnClearDb', 'btnRestartDb'].forEach(id => setRecoveryButtonDisabled(id, !dangerOk));
}

function bindRecoveryControlSync() {
  ['recoveryTargetMonth', 'recoveryTargetDate', 'recoveryBaseUnicaFile', 'recoveryBackupZipFile', 'recoveryDangerAck'].forEach((id) => {
    const el = document.getElementById(id);
    if (!el || el.dataset.boundRecoverySync === '1') return;
    el.dataset.boundRecoverySync = '1';
    el.addEventListener('input', syncRecoveryControls);
    el.addEventListener('change', syncRecoveryControls);
  });
}

function requireRecoveryDangerGate() {
  if (isRecoveryDangerAcknowledged()) return true;
  setRecoveryLog('Ação bloqueada: marque a confirmação da Zona destrutiva antes de continuar.');
  syncRecoveryControls();
  return false;
}

function defaultAutoFolderMonitorConfig() {
  return { enabled: false, stability_seconds: 20, interval_enabled: true, schedule_enabled: false, schedule_times: ['09:00', '12:00', '18:00'], folders: [] };
}

function ensureAutoFolderMonitorState() {
  state.prefs = state.prefs || {};
  state.prefs.auto_folder_monitor = state.prefs.auto_folder_monitor || defaultAutoFolderMonitorConfig();
  state.autoFolderMonitorEditingId = state.autoFolderMonitorEditingId || '';
  state.autoFolderMonitorRuntime = state.autoFolderMonitorRuntime || { running: false, last_cycle_at: '', last_cycle_message: '', folders: [] };
  state.autoFolderMonitorDraft = state.autoFolderMonitorDraft || null;
}

function autoFolderDisplayName(folder) {
  return folder.label || folder.path || 'Pasta monitorada';
}

function resetAutoFolderForm(entry = null) {
  state.autoFolderMonitorEditingId = entry?.id || '';
  const pathEl = document.getElementById('autoFolderPath');
  if (!pathEl) return;
  pathEl.value = entry?.path || '';
  document.getElementById('autoFolderLabel').value = entry?.label || '';
  document.getElementById('autoFolderInterval').value = entry?.interval_seconds || 300;
  document.getElementById('autoFolderPolicy').value = entry?.duplicate_policy || 'skip';
  document.getElementById('autoFolderActive').checked = entry ? entry.active !== false : true;
  state.autoFolderMonitorDraft = {
    path: pathEl.value,
    label: document.getElementById('autoFolderLabel').value,
    interval_seconds: Number(document.getElementById('autoFolderInterval').value || 300),
    duplicate_policy: document.getElementById('autoFolderPolicy').value || 'skip',
    active: !!document.getElementById('autoFolderActive').checked,
    dirty: false,
  };
  const status = document.getElementById('autoFolderEditStatus');
  if (status) status.textContent = entry ? `Editando pasta: ${autoFolderDisplayName(entry)}` : 'Nenhuma pasta em edição.';
}

function captureAutoFolderDraft() {
  const pathEl = document.getElementById('autoFolderPath');
  if (!pathEl) return null;
  state.autoFolderMonitorDraft = {
    path: pathEl.value,
    label: document.getElementById('autoFolderLabel').value,
    interval_seconds: Number(document.getElementById('autoFolderInterval').value || 300),
    duplicate_policy: document.getElementById('autoFolderPolicy').value || 'skip',
    active: !!document.getElementById('autoFolderActive').checked,
    dirty: true,
  };
  return state.autoFolderMonitorDraft;
}

function bindAutoFolderDraftTracking() {
  const ids = ['autoFolderPath', 'autoFolderLabel', 'autoFolderInterval', 'autoFolderPolicy', 'autoFolderActive'];
  ids.forEach((id) => {
    const el = document.getElementById(id);
    if (!el || el.dataset.boundDraft === '1') return;
    el.dataset.boundDraft = '1';
    const evt = el.tagName === 'SELECT' || el.type === 'checkbox' ? 'change' : 'input';
    el.addEventListener(evt, captureAutoFolderDraft);
  });
}

function renderAutoFolderList() {
  ensureAutoFolderMonitorState();
  const host = document.getElementById('autoFolderList');
  if (!host) return;
  const folders = state.prefs.auto_folder_monitor.folders || [];
  if (!folders.length) {
    host.innerHTML = '<div class="muted" style="font-size:12px;padding:10px 0">Nenhuma pasta monitorada cadastrada.</div>';
    return;
  }
  const runtimeById = Object.fromEntries((state.autoFolderMonitorRuntime.folders || []).map(folder => [folder.id, folder]));
  host.innerHTML = folders.map(folder => {
    const runtime = runtimeById[folder.id] || {};
    return `
      <div class="monitor-folder-row">
        <div>
          <div class="monitor-folder-row__label">${autoFolderDisplayName(folder)}</div>
          <div class="monitor-folder-row__meta">${folder.path}</div>
        </div>
        <div class="monitor-folder-row__meta">
          Intervalo: ${folder.interval_seconds}s (${Math.round(folder.interval_seconds/60)} min)<br>
          Duplicidade: ${folder.duplicate_policy === 'overwrite' ? 'Sobrescrever' : 'Ignorar'}<br>
              Última varredura: ${formatMonitorTimestamp(runtime.last_scan_at)}
        </div>
        <div>${folder.active === false ? badge('warn') : badge('ok')}</div>
        <div class="monitor-folder-row__meta">${runtime.last_result || 'Sem execução ainda'}</div>
        <div class="monitor-folder-row__meta">${runtime.last_error || 'Sem erro'}</div>
        <div class="monitoring-actions">
          <button class="btn secondary sm" onclick="editAutoFolderEntry('${folder.id.replace(/'/g, "\\'")}')">Editar</button>
          <button class="btn secondary sm" onclick="runAutoFolderEntryNow('${folder.id.replace(/'/g, "\\'")}')">Rodar agora</button>
          <button class="btn danger sm" onclick="deleteAutoFolderEntry('${folder.id.replace(/'/g, "\\'")}')">Excluir</button>
        </div>
      </div>
    `;
  }).join('');
}

function renderUploadAutoMonitorStatus() {
  const host = document.getElementById('uploadAutoMonitorStatus');
  if (!host) return;
  ensureAutoFolderMonitorState();
  const config = state.prefs.auto_folder_monitor || defaultAutoFolderMonitorConfig();
  const runtime = state.autoFolderMonitorRuntime || {};
  const activeFolders = (config.folders || []).filter(folder => folder.active !== false);
  const lastCycle = formatMonitorTimestamp(runtime.last_cycle_at);
  host.innerHTML = `
    <div class="upload-auto-monitor-card"><div class="k">Status</div><div class="v">${config.enabled ? 'Ativo' : 'Desligado'}</div><div class="m">${config.enabled ? 'Varredura periódica habilitada enquanto o app estiver aberto.' : 'Nenhuma leitura automática em execução.'}</div></div>
    <div class="upload-auto-monitor-card"><div class="k">Pastas ativas</div><div class="v">${activeFolders.length}</div><div class="m">${(config.folders || []).length} pasta(s) cadastrada(s) no total</div></div>
    <div class="upload-auto-monitor-card"><div class="k">Último ciclo</div><div class="v">${escapeHtml(lastCycle)}</div><div class="m">${escapeHtml(runtime.last_cycle_message || 'Sem execução ainda')}</div></div>
  `;
}

function renderAutoFolderMonitorLog(message) {
  const log = document.getElementById('autoFolderMonitorLog');
  if (log) log.textContent = message || 'Monitor automático ainda não configurado.';
}

function fillAutoFolderMonitorSettings() {
  ensureAutoFolderMonitorState();
  const config = state.prefs.auto_folder_monitor || defaultAutoFolderMonitorConfig();
  const enabledEl = document.getElementById('cfgAutoMonitorEnabled');
  if (enabledEl) enabledEl.checked = !!config.enabled;
  const stabilityEl = document.getElementById('cfgAutoMonitorStability');
  if (stabilityEl) stabilityEl.value = config.stability_seconds || 20;
  const intervalEnabledEl = document.getElementById('cfgAutoIntervalEnabled');
  if (intervalEnabledEl) intervalEnabledEl.checked = config.interval_enabled !== false;
  const schedEnabledEl = document.getElementById('cfgAutoScheduleEnabled');
  if (schedEnabledEl) schedEnabledEl.checked = !!config.schedule_enabled;
  const schedTimesEl = document.getElementById('cfgAutoScheduleTimes');
  if (schedTimesEl) schedTimesEl.value = (config.schedule_times || ['09:00', '12:00', '18:00']).join(', ');
  bindAutoFolderDraftTracking();
  renderAutoFolderList();
  renderUploadAutoMonitorStatus();
  renderAutoFolderMonitorLog(state.autoFolderMonitorRuntime.last_cycle_message || 'Monitor automático ainda não configurado.');
}

async function loadAutoFolderMonitorStatus() {
  ensureAutoFolderMonitorState();
  const payload = await j(`${API}/auto-folder-monitor`).catch(() => ({ config: defaultAutoFolderMonitorConfig(), runtime: { running: false, last_cycle_at: '', last_cycle_message: 'Falha ao consultar monitor.', folders: [] } }));
  state.prefs.auto_folder_monitor = payload.config || defaultAutoFolderMonitorConfig();
  state.autoFolderMonitorRuntime = payload.runtime || { running: false, last_cycle_at: '', last_cycle_message: '', folders: [] };
  fillAutoFolderMonitorSettings();
}

function collectAutoFolderConfigFromSettings() {
  ensureAutoFolderMonitorState();
  const rawTimes = (document.getElementById('cfgAutoScheduleTimes')?.value || '')
    .split(',')
    .map(t => t.trim())
    .filter(t => /^\d{2}:\d{2}$/.test(t));
  return {
    enabled: !!document.getElementById('cfgAutoMonitorEnabled')?.checked,
    stability_seconds: Number(document.getElementById('cfgAutoMonitorStability')?.value || 20),
    interval_enabled: document.getElementById('cfgAutoIntervalEnabled') ? !!document.getElementById('cfgAutoIntervalEnabled').checked : true,
    schedule_enabled: !!document.getElementById('cfgAutoScheduleEnabled')?.checked,
    schedule_times: rawTimes.length ? rawTimes : ['09:00', '12:00', '18:00'],
    folders: state.prefs.auto_folder_monitor.folders || [],
  };
}

async function persistAutoFolderMonitorConfig(message) {
  const payload = collectAutoFolderConfigFromSettings();
  const saved = await j(`${API}/auto-folder-monitor`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  state.prefs.auto_folder_monitor = saved.config || payload;
  state.autoFolderMonitorRuntime = saved.runtime || state.autoFolderMonitorRuntime;
  fillAutoFolderMonitorSettings();
  renderAutoFolderMonitorLog(message || 'Monitor automático salvo.');
}

window.editAutoFolderEntry = (folderId) => {
  ensureAutoFolderMonitorState();
  const folder = (state.prefs.auto_folder_monitor.folders || []).find(item => item.id === folderId);
  if (!folder) return;
  resetAutoFolderForm(folder);
};

window.deleteAutoFolderEntry = async (folderId) => {
  ensureAutoFolderMonitorState();
  const folder = (state.prefs.auto_folder_monitor.folders || []).find(item => item.id === folderId);
  if (!folder) return;
  if (!confirm(`Excluir a pasta monitorada ${autoFolderDisplayName(folder)}?`)) return;
  state.prefs.auto_folder_monitor.folders = (state.prefs.auto_folder_monitor.folders || []).filter(item => item.id !== folderId);
  await persistAutoFolderMonitorConfig('Pasta monitorada excluída.');
};

window.runAutoFolderEntryNow = async (folderId) => {
  const payload = await j(`${API}/auto-folder-monitor/run-now`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ folder_id: folderId }),
  });
  state.autoFolderMonitorRuntime = payload.runtime || state.autoFolderMonitorRuntime;
  renderUploadAutoMonitorStatus();
  renderAutoFolderList();
  renderAutoFolderMonitorLog((payload.results || []).map(item => `${item.label}: ${item.processed} processado(s), ${item.skipped} ignorado(s)`).join('\n') || payload.message || 'Execução manual concluída.');
  await loadProcessHistory();
  await notifyDataChanged(['upload','mpfm','separador','cards','alertas','exportar','monitoramento','xml042']);
};

function formatRecoveryPayload(payload) {
  const lines = [];
  const push = (k, v) => lines.push(`${k}: ${v}`);
  if (payload.month) push('Mês', payload.month);
  if (payload.db_path) push('SQLite', payload.db_path);
  if (payload.workbook_name) push('Workbook', payload.workbook_name);
  if (payload.workbook_exists != null) push('Workbook existe', payload.workbook_exists ? 'sim' : 'não');
  if (payload.workbook_updated_at) push('Workbook atualizado', payload.workbook_updated_at);
  if (payload.queued != null) push('Workbook em fila', payload.queued ? 'sim' : 'não');
  if (payload.state_exists != null) push('State existe', payload.state_exists ? 'sim' : 'não');
  if (payload.db_ok != null) push('Banco acessível', payload.db_ok ? 'sim' : 'não');
  if (payload.ok != null) push('Operação', payload.ok ? 'ok' : 'falhou');
  if (payload.error) push('Erro', payload.error);
  if (payload.database) {
    lines.push('Banco:');
    Object.entries(payload.database).forEach(([k, v]) => lines.push(`  - ${k}: ${v}`));
  }
  if (payload.recomputed) {
    lines.push('Recomposto:');
    Object.entries(payload.recomputed).forEach(([k, v]) => lines.push(`  - ${k}: ${v}`));
  }
  if (payload.deleted) {
    lines.push('Excluído do banco:');
    Object.entries(payload.deleted).forEach(([k, v]) => lines.push(`  - ${k}: ${v}`));
  }
  if (payload.import_summary) {
    lines.push('Resumo do Excel:');
    Object.entries(payload.import_summary).forEach(([k, v]) => lines.push(`  - ${k}: ${Array.isArray(v) ? v.join(', ') : JSON.stringify(v)}`));
  }
  if (payload.imported) {
    lines.push('Importado:');
    Object.entries(payload.imported).forEach(([k, v]) => lines.push(`  - ${k}: ${Array.isArray(v) ? v.join(', ') : JSON.stringify(v)}`));
  }
  if (payload.removed) {
    lines.push('Removido no reset:');
    Object.entries(payload.removed).forEach(([k, v]) => lines.push(`  - ${k}: ${v}`));
  }
  if (payload.health) {
    lines.push('Saúde atual da base:');
    Object.entries(payload.health).forEach(([k, v]) => lines.push(`  - ${k}: ${v}`));
  }
  if (payload.diff) {
    lines.push('Diferenças previstas:');
    Object.entries(payload.diff).forEach(([k, v]) => lines.push(`  - ${k}: ${v}`));
  }
  if (payload.affected) {
    lines.push('Escopo afetado:');
    Object.entries(payload.affected).forEach(([k, v]) => lines.push(`  - ${k}: ${Array.isArray(v) ? v.join(', ') : JSON.stringify(v)}`));
  }
  if (payload.state) {
    lines.push('State:');
    Object.entries(payload.state).forEach(([k, v]) => lines.push(`  - ${k}: ${v}`));
  }
  if (Array.isArray(payload.deleted_xml_files) && payload.deleted_xml_files.length) {
    lines.push(`XML 042 removidos: ${payload.deleted_xml_files.join(', ')}`);
  }
  if (Array.isArray(payload.hourly_coverage) && payload.hourly_coverage.length) {
    lines.push('Cobertura hourly por banco:');
    payload.hourly_coverage.forEach(row => {
      lines.push(`  - ${row.bank}: daily=${row.daily_days}, completas=${row.full_days}, parciais=${row.partial_days}, sem hourly=${row.missing_days}`);
    });
  }
  return lines.join('\n') || JSON.stringify(payload, null, 2);
}

async function refreshAfterDatabaseReset() {
  await initDates();
  await loadSummary();
  await loadOutputs();
  await loadProcessHistory();
  await notifyDataChanged(['upload','mpfm','separador','cards','alertas','exportar','monitoramento','xml042','recon','sgmfm']);
}

function renderResetResult(prefix, payload) {
  const message = formatRecoveryPayload(payload);
  const host = document.getElementById('settingsLog');
  if (host) host.textContent = `${prefix}\n${message}`;
}

async function runRecoveryAction(buttonId, url, options = {}, after = null) {
  const button = document.getElementById(buttonId);
  const log = document.getElementById('recoveryLog');
  const original = button?.textContent || '';
  try {
    if (button) {
      button.dataset.busy = '1';
      button.disabled = true;
      button.textContent = 'Processando...';
    }
    const payload = await j(url, options);
    if (log) log.textContent = formatRecoveryPayload(payload);
    if (after) await after(payload);
  } catch (err) {
    if (log) log.textContent = `Erro: ${err.message || err}`;
  } finally {
    if (button) {
      delete button.dataset.busy;
      button.disabled = false;
      button.textContent = original;
    }
    syncRecoveryControls();
  }
}

async function runRecoveryFileAction(buttonId, url, file, after = null) {
  const button = document.getElementById(buttonId);
  const log = document.getElementById('recoveryLog');
  const original = button?.textContent || '';
  try {
    if (!file) throw new Error('Selecione um arquivo .xlsx antes de continuar.');
    if (button) {
      button.dataset.busy = '1';
      button.disabled = true;
      button.textContent = 'Processando...';
    }
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(url, { method: 'POST', body: form });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(payload.detail || payload.error || `Falha HTTP ${res.status}`);
    }
    if (log) log.textContent = formatRecoveryPayload(payload);
    if (after) await after(payload);
  } catch (err) {
    if (log) log.textContent = `Erro: ${err.message || err}`;
  } finally {
    if (button) {
      delete button.dataset.busy;
      button.disabled = false;
      button.textContent = original;
    }
    syncRecoveryControls();
  }
}

document.getElementById('btnSettings').onclick = async () => {
  fillThemeModeSettings();
  fillSummaryConversionSettings();
  fillRecoverySettings();
  await loadAutoFolderMonitorStatus();
  resetAutoFolderForm();
  document.getElementById('settingsModal').classList.add('show');
};
document.getElementById('closeSettings').onclick = () => document.getElementById('settingsModal').classList.remove('show');
document.getElementById('settingsModal').addEventListener('click', e => {
  if (e.target === document.getElementById('settingsModal')) document.getElementById('settingsModal').classList.remove('show');
});
document.getElementById('btnSaveThemeMode').onclick = async () => {
  const select = document.getElementById('cfgThemeMode');
  const status = document.getElementById('themeModeStatus');
  try {
    const mode = await persistThemePreference(select?.value || 'dark');
    if (status) status.textContent = `Tema ${mode === 'light' ? 'claro' : 'escuro'} salvo.`;
  } catch (err) {
    if (status) status.textContent = `Falha ao salvar tema: ${err.message || err}`;
  }
};
document.getElementById('btnSaveSummaryConversions').onclick = async () => {
  state.prefs = state.prefs || {};
  state.prefs.summary_conversions = {
    oil_m3_to_bbl_factor: Number(document.getElementById('cfgOilM3ToBbl').value || 6.28981),
    gas_input_unit: document.getElementById('cfgGasInputUnit').value || 'Sm³',
    gas_sm3_per_boe_factor: Number(document.getElementById('cfgGasSm3PerBoe').value || 170),
    gas_boe_mode: document.getElementById('cfgGasBoeMode').value || 'Padrão corporativo',
    show_boe_criterion: !!document.getElementById('cfgShowBoeCriterion').checked,
  };
  await j(`${API}/user-prefs`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(state.prefs)});
  document.getElementById('summaryConversionStatus').textContent = 'Conversões salvas.';
  await loadSummary();
};
document.getElementById('btnOpenEquationGuide').onclick = () => {
  openEquationReferencePrintView();
};
document.getElementById('btnClearDb').onclick = async () => {
  if (!requireRecoveryDangerGate()) return;
  if (!confirm('Limpar banco SQLite, estados mensais e Excels gerados?')) return;
  const r = await j(`${API}/admin/clear-data`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({keep_backup_zip:true})});
  renderResetResult(r.ok ? '✅ Base local limpa.' : '❌ Falha ao limpar a base.', r);
  await refreshAfterDatabaseReset();
};
document.getElementById('btnRestartDb').onclick = async () => {
  if (!requireRecoveryDangerGate()) return;
  if (!confirm('Reiniciar completamente o banco local, removendo DB, WAL/SHM, states, uploads temporários e Excels gerados?')) return;
  const secondConfirm = confirm('Confirma o reinício completo do banco? Você precisará subir os dados novamente depois.');
  if (!secondConfirm) return;
  const r = await j(`${API}/admin/restart-db`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({keep_backup_zip:true})});
  renderResetResult(r.ok ? '✅ Banco reiniciado.' : '❌ Falha ao reiniciar o banco.', r);
  await refreshAfterDatabaseReset();
};
document.getElementById('btnDownloadBackupOnly').onclick = async () => {
  const r = await j(`${API}/admin/backup-only`, {method:'POST'});
  if (r.backup_file) window.open(`${API}/download/${encodeURIComponent(r.backup_file)}`, '_blank');
  renderResetResult(r.backup_file ? `✅ Backup: ${r.backup_file}\nBase preservada.` : 'Concluído.', r);
};
document.getElementById('btnDownloadBackupClear').onclick = async () => {
  if (!requireRecoveryDangerGate()) return;
  if (!confirm('Gerar backup de tudo e limpar a base?')) return;
  const r = await j(`${API}/admin/backup-and-clear`, {method:'POST'});
  if (r.backup_file) window.open(`${API}/download/${encodeURIComponent(r.backup_file)}`, '_blank');
  renderResetResult(r.backup_file ? `✅ Backup: ${r.backup_file}\nBase limpa.` : 'Concluído.', r);
  await refreshAfterDatabaseReset();
};

document.getElementById('btnRecoveryDiagnostics').onclick = async () => {
  const month = getRecoveryMonth();
  await runRecoveryAction('btnRecoveryDiagnostics', `${API}/admin/recovery/diagnostics?month=${encodeURIComponent(month)}`);
};

document.getElementById('btnRecoveryTestDb').onclick = async () => {
  await runRecoveryAction('btnRecoveryTestDb', `${API}/admin/recovery/test-db`, {method:'POST'});
};

document.getElementById('btnRecoverySyncSepMonth').onclick = async () => {
  const month = getRecoveryMonth();
  if (!month) return;
  if (!confirm(`Sincronizar o separador de ${month} usando o trio oficial de TXT, inclusive dias zerados?`)) return;
  await runRecoveryAction(
    'btnRecoverySyncSepMonth',
    `${API}/admin/recovery/sync-sep-month`,
    {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({month})},
    async () => {
      await loadSummary();
    }
  );
};

document.getElementById('btnRecoveryRecomputeMonth').onclick = async () => {
  const month = getRecoveryMonth();
  if (!month) return;
  if (!confirm(`Recompor resoluções e regenerar o workbook de ${month}?`)) return;
  await runRecoveryAction(
    'btnRecoveryRecomputeMonth',
    `${API}/admin/recovery/recompute-month`,
    {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({month})},
    async () => {
      await initDates();
      await loadSummary();
      await loadOutputs();
    }
  );
};

document.getElementById('btnRecoveryRebuildMonth').onclick = async () => {
  const month = getRecoveryMonth();
  if (!month) return;
  await runRecoveryAction(
    'btnRecoveryRebuildMonth',
    `${API}/admin/recovery/rebuild-month`,
    {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({month})},
    async () => {
      await loadOutputs();
    }
  );
};

document.getElementById('btnRecoverySanitizeImports').onclick = async () => {
  const month = getRecoveryMonth();
  if (!month) return;
  if (!confirm(`Sanear histórico duplicado de imports para ${month}?`)) return;
  await runRecoveryAction(
    'btnRecoverySanitizeImports',
    `${API}/admin/recovery/sanitize-import-history`,
    {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({month})}
  );
};

document.getElementById('btnRecoveryDeleteDay').onclick = async () => {
  if (!requireRecoveryDangerGate()) return;
  const date = getRecoveryDate();
  if (!date) {
    const log = document.getElementById('recoveryLog');
    if (log) log.textContent = 'Erro: informe o dia alvo antes de executar a exclusão.';
    return;
  }
  const firstConfirm = confirm(`Apagar completamente o dia ${date} da aplicação?`);
  if (!firstConfirm) return;
  const secondConfirm = confirm(`Confirma a exclusão total de ${date}? O upload desse dia precisará ser feito novamente.`);
  if (!secondConfirm) return;
  await runRecoveryAction(
    'btnRecoveryDeleteDay',
    `${API}/admin/recovery/delete-day`,
    {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({date})},
    async () => {
      await initDates();
      await loadSummary();
      await loadOutputs();
      await notifyDataChanged(['upload','mpfm','separador','cards','alertas','exportar','monitoramento','xml042','recon','sgmfm']);
    }
  );
};

document.getElementById('btnRecoveryPreviewBaseUnica').onclick = async () => {
  const file = getRecoveryBaseUnicaFile();
  const month = getRecoveryMonth();
  if (!month) {
    const log = document.getElementById('recoveryLog');
    if (log) log.textContent = 'Erro: selecione o mês-alvo antes de analisar o Excel.';
    return;
  }
  await runRecoveryFileAction(
    'btnRecoveryPreviewBaseUnica',
    `${API}/admin/recovery/base-unica-import/preview?month=${encodeURIComponent(month)}`,
    file,
  );
};

document.getElementById('btnRecoveryApplyBaseUnica').onclick = async () => {
  if (!requireRecoveryDangerGate()) return;
  const file = getRecoveryBaseUnicaFile();
  const month = getRecoveryMonth();
  if (!file) {
    const log = document.getElementById('recoveryLog');
    if (log) log.textContent = 'Erro: selecione um workbook .xlsx com BASE_UNICA_MES ou BASE_UNICA_TOTAL.';
    return;
  }
  if (!month) {
    const log = document.getElementById('recoveryLog');
    if (log) log.textContent = 'Erro: selecione o mês-alvo antes de aplicar o Excel.';
    return;
  }
  const firstConfirm = confirm(`Aplicar importação soberana do workbook ${file.name}?`);
  if (!firstConfirm) return;
  const secondConfirm = confirm(`Confirma substituir ${month} pelo conteúdo do Excel? Essa ação remove o estado atual do mês para refletir exatamente o arquivo.`);
  if (!secondConfirm) return;
  await runRecoveryFileAction(
    'btnRecoveryApplyBaseUnica',
    `${API}/admin/recovery/base-unica-import/apply?month=${encodeURIComponent(month)}`,
    file,
    async () => {
      await initDates();
      await loadSummary();
      await loadOutputs();
      await notifyDataChanged(['upload','mpfm','separador','cards','alertas','exportar','monitoramento','xml042','recon']);
    }
  );
};

document.getElementById('btnRecoveryRestoreBackupZip').onclick = async () => {
  if (!requireRecoveryDangerGate()) return;
  const file = getRecoveryBackupZipFile();
  const log = document.getElementById('recoveryLog');
  if (!file) {
    if (log) log.textContent = 'Erro: selecione um backup ZIP antes de continuar.';
    return;
  }
  const firstConfirm = confirm(`Restaurar o backup ${file.name} nesta instalação?`);
  if (!firstConfirm) return;
  const secondConfirm = confirm('Confirma substituir a base local, cadastro, estados e workbooks pelo conteúdo do ZIP? Um backup de segurança do estado atual será criado antes da restauração.');
  if (!secondConfirm) return;
  await runRecoveryFileAction(
    'btnRecoveryRestoreBackupZip',
    `${API}/admin/recovery/backup-zip/restore`,
    file,
    async () => {
      await refreshAfterDatabaseReset();
    }
  );
};

document.getElementById('btnSaveAutoMonitorConfig').onclick = async () => {
  await persistAutoFolderMonitorConfig('Configuração global do monitor salva.');
};

document.getElementById('btnSaveAutoFolderEntry').onclick = async () => {
  ensureAutoFolderMonitorState();
  const path = document.getElementById('autoFolderPath')?.value.trim();
  if (!path) {
    renderAutoFolderMonitorLog('Informe o caminho da pasta monitorada.');
    return;
  }
  const entry = {
    id: state.autoFolderMonitorEditingId || `folder-${Date.now()}`,
    path,
    label: document.getElementById('autoFolderLabel')?.value.trim() || '',
    interval_seconds: Number(document.getElementById('autoFolderInterval')?.value || 300),
    duplicate_policy: document.getElementById('autoFolderPolicy')?.value || 'skip',
    active: !!document.getElementById('autoFolderActive')?.checked,
  };
  const folders = [...(state.prefs.auto_folder_monitor.folders || [])];
  const index = folders.findIndex(item => item.id === entry.id);
  if (index >= 0) folders[index] = entry;
  else folders.push(entry);
  state.prefs.auto_folder_monitor.folders = folders;
  resetAutoFolderForm();
  await persistAutoFolderMonitorConfig('Pasta monitorada salva.');
};

document.getElementById('btnResetAutoFolderEntry').onclick = () => resetAutoFolderForm();

const btnBrowseFolder = document.getElementById('btnBrowseFolder');
if (btnBrowseFolder) {
  btnBrowseFolder.onclick = async () => {
    const original = btnBrowseFolder.textContent;
    btnBrowseFolder.disabled = true;
    btnBrowseFolder.textContent = '⏳ Abrindo...';
    try {
      const res = await j(`${API}/browse-folder`);
      if (res.ok && res.path) {
        const pathEl = document.getElementById('autoFolderPath');
        if (pathEl) {
          pathEl.value = res.path;
          pathEl.dispatchEvent(new Event('input'));
        }
      }
    } catch (err) {
      renderAutoFolderMonitorLog(`Não foi possível abrir o seletor de pasta: ${err.message || err}`);
    } finally {
      btnBrowseFolder.disabled = false;
      btnBrowseFolder.textContent = original;
    }
  };
}

async function runAutoFolderMonitorNow(buttonId, folderId = null) {
  const button = document.getElementById(buttonId);
  const original = button?.textContent || '';
  try {
    if (button) {
      button.disabled = true;
      button.textContent = 'Processando...';
    }
    const payload = await j(`${API}/auto-folder-monitor/run-now`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(folderId ? { folder_id: folderId } : {}),
    });
    state.autoFolderMonitorRuntime = payload.runtime || state.autoFolderMonitorRuntime;
    fillAutoFolderMonitorSettings();
    renderAutoFolderMonitorLog((payload.results || []).map(item => `${item.label}: ${item.processed} processado(s), ${item.skipped} ignorado(s)`).join('\n') || payload.message || 'Execução manual concluída.');
    await loadProcessHistory();
    await notifyDataChanged(['upload','mpfm','separador','cards','alertas','exportar','monitoramento','xml042']);
  } catch (err) {
    renderAutoFolderMonitorLog(`Erro ao executar monitor: ${err.message || err}`);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = original;
    }
  }
}

const btnRunAutoMonitorConfigNow = document.getElementById('btnRunAutoMonitorConfigNow');
if (btnRunAutoMonitorConfigNow) {
  btnRunAutoMonitorConfigNow.onclick = async () => {
    await runAutoFolderMonitorNow('btnRunAutoMonitorConfigNow');
  };
}

const btnRunAutoFolderNow = document.getElementById('btnRunAutoFolderNow');
if (btnRunAutoFolderNow) {
  btnRunAutoFolderNow.onclick = async () => {
    await runAutoFolderMonitorNow('btnRunAutoFolderNow');
  };
}

const btnOpenAutoFolderSettings = document.getElementById('btnOpenAutoFolderSettings');
if (btnOpenAutoFolderSettings) {
  btnOpenAutoFolderSettings.onclick = async () => {
    await loadAutoFolderMonitorStatus();
    resetAutoFolderForm();
    document.getElementById('settingsModal').classList.add('show');
  };
}

