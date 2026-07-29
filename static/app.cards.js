'use strict';

const DEADLINE_PERIOD_LABELS = {
  custom: 'Definido pelo usuário',
  daily: 'Diário',
  weekly: 'Semanal',
  monthly: 'Mensal',
  quarterly: 'Trimestral',
  semiannual: 'Semestral',
  annual: 'Anual',
};

function deadlineParseDate(value) {
  if (!value) return null;
  const parts = String(value).split('-').map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return null;
  return new Date(parts[0], parts[1] - 1, parts[2]);
}

function deadlineFormatDate(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function deadlineAddMonths(baseDate, months) {
  const targetMonthIndex = baseDate.getMonth() + months;
  const year = baseDate.getFullYear() + Math.floor(targetMonthIndex / 12);
  const month = ((targetMonthIndex % 12) + 12) % 12;
  const lastDay = new Date(year, month + 1, 0).getDate();
  return new Date(year, month, Math.min(baseDate.getDate(), lastDay));
}

function deadlineComputeDueDate(startDate, periodicity, periodicityDays) {
  const base = deadlineParseDate(startDate);
  if (!base) return '';
  switch ((periodicity || 'custom').toLowerCase()) {
    case 'daily':
      return deadlineFormatDate(new Date(base.getFullYear(), base.getMonth(), base.getDate() + 1));
    case 'weekly':
      return deadlineFormatDate(new Date(base.getFullYear(), base.getMonth(), base.getDate() + 7));
    case 'monthly':
      return deadlineFormatDate(deadlineAddMonths(base, 1));
    case 'quarterly':
      return deadlineFormatDate(deadlineAddMonths(base, 3));
    case 'semiannual':
      return deadlineFormatDate(deadlineAddMonths(base, 6));
    case 'annual':
      return deadlineFormatDate(deadlineAddMonths(base, 12));
    default:
      return Number(periodicityDays || 0) > 0
        ? deadlineFormatDate(new Date(base.getFullYear(), base.getMonth(), base.getDate() + Number(periodicityDays)))
        : '';
  }
}

function syncDeadlineDueDate() {
  const startEl = document.getElementById('dlStart');
  const dueEl = document.getElementById('dlDue');
  const periodicityEl = document.getElementById('dlPeriodicity');
  const periodDaysEl = document.getElementById('dlPeriodDays');
  if (!startEl || !dueEl || !periodicityEl || !periodDaysEl) return;
  const isCustom = periodicityEl.value === 'custom';
  periodDaysEl.disabled = !isCustom;
  if (!isCustom) periodDaysEl.value = '0';
  // Read ISO value: dataset.isoValue is set by enhanceBrazilianDateInputs; fall back to
  // parseBrDateToIso so BR-formatted text (dd/mm/aaaa) and ISO values both parse correctly.
  const startIso = startEl.dataset.isoValue
    || (typeof parseBrDateToIso === 'function' ? parseBrDateToIso(startEl.value || '') : '')
    || '';
  const computed = deadlineComputeDueDate(startIso, periodicityEl.value, periodDaysEl.value);
  if (computed) {
    dueEl.dataset.isoValue = computed;
    dueEl.value = computed;
    if (typeof refreshDateInputDisplay === 'function') refreshDateInputDisplay(document);
  }
  if (!startIso) {
    dueEl.dataset.isoValue = '';
    dueEl.value = '';
    if (typeof refreshDateInputDisplay === 'function') refreshDateInputDisplay(document);
  }
}

function renderDeadlineIndicators(rows) {
  const host = document.getElementById('deadlineIndicators');
  if (!host) return;
  const items = (rows || []).filter(it => !it.is_closed);
  const above60 = items.filter(it => (it.days_remaining ?? 99999) > 60).length;
  const groups = [
    ['Vencidos', items.filter(it => (it.days_remaining ?? 99999) < 0).length, '⛔', 'itens com prazo vencido', 'deadline-indicator deadline-indicator--crit'],
    ['Até 15 dias', items.filter(it => (it.days_remaining ?? 99999) >= 0 && it.days_remaining <= 15).length, '15', 'prioridade imediata', 'deadline-indicator deadline-indicator--warn15'],
    ['16 a 30 dias', items.filter(it => (it.days_remaining ?? 99999) > 15 && it.days_remaining <= 30).length, '30', 'janela curta', 'deadline-indicator deadline-indicator--warn30'],
    ['31 a 60 dias', items.filter(it => (it.days_remaining ?? 99999) > 30 && it.days_remaining <= 60).length, '60', 'planejamento próximo', 'deadline-indicator deadline-indicator--info60'],
    ['Acima de 60 dias', above60, '60+', 'itens fora da janela curta', 'deadline-indicator deadline-indicator--info60'],
  ];
  const cardsHtml = groups.map(([label, value, icon, meta, cls]) => `
    <div class="${cls}">
      <div class="deadline-indicator__icon">${escapeHtml(icon)}</div>
      <div>
        <div class="deadline-indicator__label">${escapeHtml(label)}</div>
        <div class="deadline-indicator__value">${value}</div>
        <div class="muted" style="font-size:11px;margin-top:4px">${escapeHtml(meta)}</div>
      </div>
    </div>
  `).join('');
  host.innerHTML = cardsHtml;
}

function resetDeadlineForm() {
  document.getElementById('btnSaveDeadline').dataset.editId = '';
  document.getElementById('dlSubject').value = '';
  document.getElementById('dlCategory').value = 'Verificação';
  document.getElementById('dlNorm').value = '';
  document.getElementById('dlRisk').value = '';
  document.getElementById('dlStart').value = '';
  document.getElementById('dlDue').value = '';
  document.getElementById('dlPeriodicity').value = 'custom';
  document.getElementById('dlPeriodDays').value = '0';
  if (typeof refreshDateInputDisplay === 'function') refreshDateInputDisplay(document);
  document.getElementById('dlEvidence').value = '';
  document.getElementById('dlAction').value = '';
  document.getElementById('dlNotes').value = '';
  document.getElementById('dlIcon').value = 'deadlines';
  syncDeadlineDueDate();
}

window.editSummaryIcon = async (label) => {
  const current = ((state.prefs&&state.prefs.summary_icons)||{})[label] || '';
  const icon = prompt(`Ícone para ${label}:\nUse emoji, nome do ícone (oil, gas, water, hc, boe, barrel...) ou arquivo .png em /static/icons/.`, current || 'summary');
  if (icon === null) return;
  state.prefs = state.prefs || {};
  state.prefs.summary_icons = Object.assign({}, state.prefs.summary_icons || {}, {[label]: icon || 'summary'});
  await j(`${API}/user-prefs`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(state.prefs)}).catch(()=>null);
  loadSummary();
};

async function loadDeadlinesSummary(){
  const d = await j(`${API}/deadlines`).catch(()=>({items:[]}));
  const items = (d.items||[]).filter(it => !it.is_closed).sort((a,b)=> (a.days_remaining??99999) - (b.days_remaining??99999)).slice(0,4);
  const host = document.getElementById('deadlineSummary'); if(!host) return;
  host.innerHTML = items.length ? items.map(it=>{
    const cls = (it.days_remaining==null)?'deadline-ok':(it.days_remaining<0?'deadline-crit':it.days_remaining<=10?'deadline-warn':'deadline-ok');
    return `<div class="deadline-card"><div class="top"><div class="deadline-icon-wrap">${renderIconMarkup(it.icon,'deadlines','deadline-icon')}</div><span class="deadline-badge ${cls}">${escapeHtml(it.status)}</span></div><div class="subject">${escapeHtml(it.subject)}</div><div class="days">${it.days_remaining==null?'—':it.days_remaining}</div><div style="font-size:11px;color:var(--muted);text-align:center">dias restantes</div><div class="meta"><div>Início<strong>${it.start_date?fmtDate(it.start_date):'—'}</strong></div><div>Limite<strong>${it.due_date?fmtDate(it.due_date):'—'}</strong></div></div></div>`;
  }).join('') : '<div class="muted">Nenhum prazo cadastrado.</div>';
}

async function loadDeadlines(){
  const [d] = await Promise.all([
    j(`${API}/deadlines`).catch(()=>({items:[]})),
    loadFlowTraceDeadlines(),
  ]);
  const rows = d.items || [];
  renderDeadlineIndicators(rows);
  document.getElementById('deadlineRows').innerHTML = rows.map(it=>{
    const cls = it.is_closed ? 'deadline-ok' : (it.days_remaining==null)?'deadline-ok':(it.days_remaining<0?'deadline-crit':it.days_remaining<=10?'deadline-warn':'deadline-ok');
    const periodicityLabel = it.periodicity==='custom'
      ? (it.periodicity_days ? `${it.periodicity_days} dias` : (it.periodicity_label || DEADLINE_PERIOD_LABELS.custom))
      : (it.periodicity_label || DEADLINE_PERIOD_LABELS[it.periodicity] || it.periodicity);
    const risk = it.risk_level || '—';
    return `<tr><td>${renderIconMarkup(it.icon,'deadlines','deadline-icon deadline-icon--table')}</td><td>${escapeHtml(it.subject)}</td><td>${escapeHtml(it.category||'—')}</td><td>${escapeHtml(it.norm_ref||'—')}</td><td>${escapeHtml(risk)}</td><td>${it.start_date?fmtDate(it.start_date):'—'}</td><td>${it.due_date?fmtDate(it.due_date):'—'}</td><td>${escapeHtml(periodicityLabel)}</td><td class="mono">${it.is_closed?'—':(it.days_remaining==null?'—':it.days_remaining)}</td><td><span class="deadline-badge ${cls}">${escapeHtml(it.status)}</span></td><td>${escapeHtml(it.notes||it.evidence_required||'')}</td><td>${escapeHtml(it.recommended_action||'—')}</td><td><button class="btn secondary sm" onclick="editDeadline(${it.id})">Editar</button> <button class="btn danger sm" onclick="deleteDeadline(${it.id})">Excluir</button></td></tr>`;
  }).join('') || '<tr><td colspan="13" class="muted">Sem prazos cadastrados.</td></tr>';
  state.deadlines = rows;
}

function flowTraceTypeLabel(type) {
  return ({
    nota: 'Nota',
    evidencia: 'Evidência',
    pendencia: 'Pendência',
    decisao: 'Decisão',
    revisao: 'Revisão',
  })[type] || type || 'Registro';
}

function flowTraceStatusLabel(status) {
  return ({
    aberto: 'Aberto',
    em_andamento: 'Em andamento',
    resolvido: 'Resolvido',
    cancelado: 'Cancelado',
  })[status] || status || 'Aberto';
}

function flowTraceStatusClass(status) {
  if (status === 'resolvido') return 'deadline-ok';
  if (status === 'cancelado') return 'deadline-crit';
  if (status === 'em_andamento') return 'deadline-warn';
  return 'deadline-warn';
}

function flowTracePayload(item) {
  if (!item) return {};
  if (item.payload && typeof item.payload === 'object') return item.payload;
  try { return JSON.parse(item.payload_json || '{}'); } catch (_) { return {}; }
}

async function loadFlowTraceDeadlines() {
  const rowsHost = document.getElementById('flowTraceDeadlineRows');
  if (!rowsHost) return;
  const meta = document.getElementById('flowTraceDeadlineMeta');
  const data = await j(`${API}/methodology-flow/items?limit=120`).catch(() => ({items: []}));
  const rows = (data.items || []).filter((item) => ['pendencia', 'revisao'].includes(String(item.item_type || '')));
  const openRows = rows.filter((item) => !['resolvido', 'cancelado'].includes(String(item.status || 'aberto')));
  state.flowTraceItems = rows;
  if (meta) meta.textContent = `${openRows.length} item(ns) em aberto · ${rows.length} registro(s) rastreáveis ligados ao Fluxo/Assistente.`;
  rowsHost.innerHTML = rows.map((item) => {
    const payload = flowTracePayload(item);
    const step = payload.step_id || payload.methodology_flow_context?.active_step || item.item_key || '';
    const hour = payload.hour ?? payload.methodology_flow_context?.active_hour;
    const origin = payload.source || payload.created_from_ui || payload.methodology_flow_context?.source || 'fluxo';
    const status = String(item.status || 'aberto');
    const cls = flowTraceStatusClass(status);
    const stepHour = [step ? `etapa ${step}` : '', hour !== undefined && hour !== null && hour !== '' ? `${String(hour).padStart(2, '0')}:00` : ''].filter(Boolean).join(' · ') || 'run completo';
    const isDone = ['resolvido', 'cancelado'].includes(status);
    return `
      <tr>
        <td>${escapeHtml(flowTraceTypeLabel(item.item_type))}</td>
        <td><span class="deadline-badge ${cls}">${escapeHtml(flowTraceStatusLabel(status))}</span></td>
        <td class="mono">#${escapeHtml(item.run_id || '-')}</td>
        <td>${escapeHtml(stepHour)}</td>
        <td><strong>${escapeHtml(item.title || 'Registro sem título')}</strong></td>
        <td>${escapeHtml(item.summary || '').slice(0, 180)}</td>
        <td>${escapeHtml(origin)}</td>
        <td>
          <button class="btn secondary sm" type="button" onclick="openFlowTraceInFluxo(${Number(item.id)})">Fluxo</button>
          ${isDone ? '' : `<button class="btn secondary sm" type="button" onclick="resolveFlowTraceItem(${Number(item.id)})">Concluir</button>`}
        </td>
      </tr>`;
  }).join('') || '<tr><td colspan="8" class="muted">Sem pendências ou revisões rastreáveis em aberto.</td></tr>';
}

window.openFlowTraceInFluxo = (id) => {
  state.flowTraceSelectedId = id;
  if (typeof setPage === 'function') setPage('fluxo');
};

window.resolveFlowTraceItem = async (id) => {
  const item = (state.flowTraceItems || []).find((row) => Number(row.id) === Number(id));
  if (!item) return;
  const payload = flowTracePayload(item);
  await j(`${API}/methodology-flow/items/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      run_id: item.run_id || null,
      item_type: item.item_type || 'pendencia',
      scope: item.scope || 'run',
      item_key: item.item_key || '',
      title: item.title || 'Registro da trilha',
      status: 'resolvido',
      owner: item.owner || '',
      due_date: item.due_date || '',
      summary: item.summary || '',
      payload: {...payload, resolved_from: 'prazos'},
    }),
  });
  await loadFlowTraceDeadlines();
};
window.editDeadline = (id) => {
  const it = (state.deadlines||[]).find(x=>x.id===id); if(!it) return;
  document.getElementById('dlSubject').value = it.subject||'';
  document.getElementById('dlCategory').value = it.category||'Outro';
  if (!document.getElementById('dlCategory').value) document.getElementById('dlCategory').value = 'Outro';
  document.getElementById('dlNorm').value = it.norm_ref||'';
  document.getElementById('dlRisk').value = it.risk_level||'';
  document.getElementById('dlStart').value = it.start_date||'';
  document.getElementById('dlDue').value = it.due_date||'';
  document.getElementById('dlPeriodicity').value = it.periodicity||'custom';
  document.getElementById('dlPeriodDays').value = it.periodicity_days||0;
  if (typeof refreshDateInputDisplay === 'function') refreshDateInputDisplay(document);
  document.getElementById('dlEvidence').value = it.evidence_required||'';
  document.getElementById('dlAction').value = it.recommended_action||'';
  document.getElementById('dlNotes').value = it.notes||'';
  document.getElementById('dlIcon').value = it.icon||'⏳';
  document.getElementById('btnSaveDeadline').dataset.editId = id;
  document.getElementById('deadlineFormStatus').textContent = `Editando prazo #${id}.`;
  syncDeadlineDueDate();
};
window.deleteDeadline = async (id) => {
  if(!confirm('Excluir prazo?')) return;
  try {
    const res = await fetch(`${API}/deadlines/${id}`, {method:'DELETE'});
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}));
      throw new Error(payload.detail || payload.error || `Falha HTTP ${res.status}`);
    }
    await loadDeadlines();
    await loadDeadlinesSummary();
  } catch(err) {
    document.getElementById('deadlineFormStatus').textContent = `Erro ao excluir: ${err.message}`;
  }
};
document.getElementById('btnSaveDeadline').onclick = async ()=>{
  const subjectEl = document.getElementById('dlSubject');
  const categoryEl = document.getElementById('dlCategory');
  const startEl = document.getElementById('dlStart');
  const dueEl = document.getElementById('dlDue');
  const periodicityEl = document.getElementById('dlPeriodicity');
  const periodDaysEl = document.getElementById('dlPeriodDays');
  const normEl = document.getElementById('dlNorm');
  const riskEl = document.getElementById('dlRisk');
  const evidenceEl = document.getElementById('dlEvidence');
  const actionEl = document.getElementById('dlAction');
  const notesEl = document.getElementById('dlNotes');
  const iconEl = document.getElementById('dlIcon');
  const statusEl = document.getElementById('deadlineFormStatus');
  syncDeadlineDueDate();
  const body = {
    id: document.getElementById('btnSaveDeadline').dataset.editId || undefined,
    subject: subjectEl.value.trim(),
    category: categoryEl.value,
    start_date: startEl.value,
    due_date: dueEl.value,
    periodicity: periodicityEl.value,
    periodicity_days: Number(periodDaysEl.value || 0),
    norm_ref: normEl.value.trim(),
    risk_level: riskEl.value,
    evidence_required: evidenceEl.value.trim(),
    recommended_action: actionEl.value.trim(),
    notes: notesEl.value.trim(),
    icon: iconEl.value.trim() || 'deadlines',
  };
  if (!body.subject) {
    statusEl.textContent = 'Informe o assunto antes de salvar.';
    return;
  }
  try {
    const resp = await j(`${API}/deadlines`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    resetDeadlineForm();
    statusEl.textContent = resp?.ok ? 'Prazo salvo.' : 'Falha ao salvar prazo.';
    await loadDeadlines();
    await loadDeadlinesSummary();
  } catch (_err) {
    statusEl.textContent = 'Falha ao salvar prazo.';
  }
};
document.getElementById('btnLoadDeadlines').onclick = ()=>{ loadDeadlines(); loadDeadlinesSummary(); };
document.getElementById('btnLoadFlowTraceDeadlines')?.addEventListener('click', loadFlowTraceDeadlines);
async function runDeadlineExcelImport(dryRun) {
  const pathEl = document.getElementById('deadlineImportPath');
  const statusEl = document.getElementById('deadlineImportStatus');
  if (!pathEl || !statusEl) return;
  const path = pathEl.value.trim();
  if (!path) {
    statusEl.textContent = 'Informe o caminho do Excel de controle.';
    return;
  }
  statusEl.textContent = dryRun ? 'Lendo prévia da planilha...' : 'Importando e atualizando prazos...';
  try {
    const res = await j(`${API}/deadlines/import-excel`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({path, dry_run: dryRun}),
    });
    const categories = Object.entries(res.by_category || {}).map(([k, v]) => `${k}: ${v}`).join(' · ');
    const action = dryRun ? 'Prévia' : `Importação concluída (${res.inserted || 0} novos, ${res.updated || 0} atualizados)`;
    statusEl.textContent = `${action}. ${res.items_built || 0} item(ns) extraídos. ${categories}`;
    if (!dryRun) {
      await loadDeadlines();
      await loadDeadlinesSummary();
    }
  } catch (err) {
    statusEl.textContent = `Falha na importação: ${err.message || err}`;
  }
}
document.getElementById('btnPreviewDeadlineExcel')?.addEventListener('click', () => runDeadlineExcelImport(true));
document.getElementById('btnImportDeadlineExcel')?.addEventListener('click', () => runDeadlineExcelImport(false));
document.getElementById('dlStart').addEventListener('change', syncDeadlineDueDate);
// blur covers the case where the user types a date manually (text mode) and tabs away
document.getElementById('dlStart').addEventListener('blur', () => setTimeout(syncDeadlineDueDate, 0));
document.getElementById('dlPeriodicity').addEventListener('change', syncDeadlineDueDate);
document.getElementById('dlPeriodDays').addEventListener('input', syncDeadlineDueDate);
syncDeadlineDueDate();

function pctStyle(v){ if(v==null) return 'background:#f3f4f6;color:#222'; return Math.abs(v)<=7?'background:#d9ead3;color:#1f3b08':'background:#f4cccc;color:#6a0000'; }
function balTone(v){ if(v==null) return {bg:'#eceff4',fg:'#1b2430'}; return Math.abs(v)<=7?{bg:'#d9ead3',fg:'#1f3b08'}:{bg:'#f4cccc',fg:'#6a0000'}; }
function renderMetricCell(title, unit, value, headColor, valueColor='#111', headSize=13){
  return `<div style="display:flex;flex-direction:column;border:1px solid #16304f;background:#fff;min-height:72px"><div style="background:${headColor};color:#fff;font-weight:700;text-align:center;padding:7px 4px;font-size:${headSize}px;line-height:1.15">${title}<br><span style='font-size:11px;opacity:.95'>${unit||''}</span></div><div style="background:#fff;color:${valueColor};text-align:center;padding:10px 4px;font-size:18px;font-weight:800">${value}</div></div>`;
}
function renderEditableCell(title, unit, field, value, id){
  return `<div style="display:flex;flex-direction:column;border:1px solid #16304f;background:#fff;min-height:72px"><div style="background:#1774ba;color:#fff;font-weight:700;text-align:center;padding:7px 4px;font-size:12px;line-height:1.15">${title}<br><span style='font-size:11px;opacity:.95'>${unit||''}</span></div><div style="background:#fff;padding:8px 6px"><input data-field="${field}" data-id="${id}" value="${value??''}" style="width:100%;text-align:center;font-size:18px;font-weight:800;border:none;outline:none;background:#fff;color:#111"></div></div>`;
}
function cardHtml(c){
  const id = c.manual?.id || '';
  const key = btoa(unescape(encodeURIComponent(JSON.stringify({production_date:c.production_date, bank:c.bank, card_type:c.card_type, tag:c.tag||'', instrument:c.instrument||'', title:c.title||''}))));
  const num = x => x==null || x==='' || Number.isNaN(Number(x)) ? '—' : Number(x).toLocaleString('pt-BR',{maximumFractionDigits:4});
  const pct = x => x==null || x==='' || Number.isNaN(Number(x)) ? '—' : `${Number(x).toFixed(2)}%`;
  const ratio = (a,b) => (a==null||b==null||!Number(b)) ? '—' : `${(Number(a)/Number(b)).toFixed(3)}`;
  const tone = (x, y=7, z=10) => {
    const v = Math.abs(Number(x||0));
      if (v > z) return {bg:'#5A1E1E', fg:'#fff', bgLight:'#FDECEC', fgLight:'#8F1D1D'};
      if (v > y) return {bg:'#7A5C00', fg:'#fff', bgLight:'#FFF6DB', fgLight:'#8A5A00'};
      return {bg:'#1B4332', fg:'#fff', bgLight:'#E8F6EE', fgLight:'#20603F'};
  };
  const masses={oil_t:Number(c.masses?.oil_t||0), gas_t:Number(c.masses?.gas_t||0), water_t:Number(c.masses?.water_t||0)};
  const hc = (c.masses?.oil_t==null && c.masses?.gas_t==null) ? null : masses.oil_t + masses.gas_t;
  const total = (c.masses?.oil_t==null && c.masses?.gas_t==null && c.masses?.water_t==null) ? null : masses.oil_t + masses.gas_t + masses.water_t;
  const hcTone = tone(c.balance?.hc_pct, 7, 10);
  const tgTone = tone(c.balance?.total_pct, 5, 7);
  const obs = c.observations || '';
  const hdr2 = `${c.bank||'—'} · ${String(c.card_type||'').toUpperCase()} ${c.instrument || c.tag || ''}`.trim();
  return `<div class="daily-card" data-card-key="${key}">
    <div class="daily-card__header1">BACALHAU FPSO · DASHBOARD DIÁRIO · MEDIÇÃO MULTIFÁSICA</div>
    <div class="daily-card__header2">${hdr2}</div>
    <div class="daily-card__date">${fmtDate(c.production_date)}</div>
    <div class="daily-card__grid">
      ${cardSection('  ▸  VOLUME', [
        ['🛢 Volume [sm³]', num(c.volumes?.oil_sm3)],
        ['💨 Volume [msm³]', num(c.volumes?.gas_msm3)],
        ['💧 Volume [sm³]', num(c.volumes?.water_sm3)]
      ], ['📊','📊','📊'])}
      ${cardSection('  ▸  MASSA', [
        ['🛢 Massa [t]', num(c.masses?.oil_t)],
        ['💨 Massa [t]', num(c.masses?.gas_t)],
        ['💧 Massa [t]', num(c.masses?.water_t)]
      ], ['⚖️','⚖️','⚖️'])}
      ${cardSection('  ▸  HC / TOTAL', [
        ['🔥 HC [t]', num(hc)],
        ['🔥 Total [t]', num(total)],
        ['🔥 HC/Total', ratio(hc,total)]
      ], ['🔥','🔥','🔥'])}
      <div class="daily-card__section">
        <div class="daily-card__section-title">  ⚡  BALANÇO  SUBSEA × TOPSIDE</div>
        <div class="daily-card__row3">
          ${metricBox('Desvio HC [%]', pct(c.balance?.hc_pct), hcTone)}
          ${metricBox('Desvio Total [%]', pct(c.balance?.total_pct), tgTone)}
          ${metricBox('MPFM x Fiscal [%]', pct(c.balance?.mpfm_x_fiscal_pct), tone(c.balance?.mpfm_x_fiscal_pct,7,10))}
        </div>
        <div class="daily-card__status-row">
          <div class="metric-box"><div class="metric-box__label">🎯 Status</div><div class="metric-box__value" style="font-size:16px">${Math.abs(Number(c.balance?.hc_pct||0))>10||Math.abs(Number(c.balance?.total_pct||0))>7?'🔴 ALERTA':(Math.abs(Number(c.balance?.hc_pct||0))>7||Math.abs(Number(c.balance?.total_pct||0))>5?'⚠️ ATENÇÃO':'✅ CONFORME')}</div></div>
          <div class="metric-box"><div class="metric-box__label">ℹ️ Limites</div><div class="metric-box__value" style="font-size:16px">±7% | ±10%</div></div>
        </div>
      </div>
      <div class="daily-card__section">
        <div class="daily-card__section-title">  🔧  VARIÁVEIS OPERACIONAIS</div>
        <div class="daily-card__row3">
          ${editMetric('📡 P [barg]', num(c.control?.pressure_barg))}
          ${editMetric('🌡️ T [°c]', num(c.control?.temperature_c))}
          ${editInput('⚡ Vel [m/s]', 'flow_velocity_ms', c.control?.flow_velocity_ms)}
        </div>
        <div class="daily-card__row3">
          ${editMetric('ρ gás [kg/m³]', num(c.control?.dens_gas))}
          ${editMetric('ρ óleo [kg/m³]', num(c.control?.dens_oil))}
          ${editInput('📊 dP [mbar]', 'dp_value', c.control?.dp_value)}
        </div>
        <div class="daily-card__row3">
          ${bubbleBox(c.control?.bubble_point)}
          ${editSelect('🔗 Alinhado ao separador?', 'sep_test_aligned', c.control?.sep_test_aligned, ['', 'Sim', 'Não'])}
          ${editMetric('ρ água [kg/m³]', num(c.control?.dens_water))}
        </div>
      </div>
      <div class="daily-card__section daily-card__section--full">
        <div class="daily-card__section-title">  💰  FISCAL & GÁS</div>
        <div class="daily-card__row3 fiscal-grid">
          ${metricBox('Var. Fiscal Óleo [%]', pct(c.balance?.mpfm_x_fiscal_pct), tone(c.balance?.mpfm_x_fiscal_pct,7,10))}
          ${metricBox('Balanço Gás [%]', pct(c.balance?.balanco_gas_pct), tone(c.balance?.balanco_gas_pct,7,10))}
          <div class="obs-box"><div class="metric-box__label">📝 Observações</div><textarea data-field="observations">${obs}</textarea></div>
        </div>
      </div>
      <div class="daily-card__actions">
        <button class="btn secondary sm" onclick="saveCardByKey('${key}')">Salvar</button>
        ${id?`<button class="btn secondary sm" onclick="deleteCard(${id})">Excluir</button>`:''}
      </div>
    </div>
  </div>`;
}
function metricBox(label, value, tone={bg:'#0F2233',fg:'#fff',bgLight:'#F7F9FC',fgLight:'#122033'}){
  const bg = tone?.bg || '#0F2233';
  const fg = tone?.fg || '#fff';
  const bgLight = tone?.bgLight || '#F7F9FC';
  const fgLight = tone?.fgLight || '#122033';
  return `<div class="metric-box metric-box--tone" style="--metric-bg:${bg};--metric-fg:${fg};--metric-bg-light:${bgLight};--metric-fg-light:${fgLight}"><div class="metric-box__label">${label}</div><div class="metric-box__value">${value}</div></div>`
}
function editMetric(label, value){return `<div class="metric-box"><div class="metric-box__label">${label}</div><div class="metric-box__value">${value}</div></div>`}
function editInput(label, field, value){return `<div class="metric-box"><div class="metric-box__label">${label}</div><input class="metric-box__input" data-field="${field}" value="${value ?? ''}"></div>`}
function editSelect(label, field, value, options){ return `<div class="metric-box"><div class="metric-box__label">${label}</div><select class="metric-box__input" data-field="${field}">${options.map(o=>`<option value="${o}" ${String(value||'')===String(o)?'selected':''}>${o||'—'}</option>`).join('')}</select></div>` }
function bubbleBox(bp){ const tone={bg:(bp?.color||'#374151'),fg:'#fff',bgLight:'#EEF2F7',fgLight:'#243447'}; return metricBox('🫧 Ponto de bolha', `${bp?.icon||'⚪'} ${bp?.label||'N/D'}`, tone); }
function cardSection(title, items, icons){
  return `<div class="daily-card__section"><div class="daily-card__section-title">${title}</div><div class="daily-card__row3">${items.map(([lab,val],i)=>`<div class="metric-box"><div class="metric-box__label">${lab}</div><div class="metric-box__value">${val}</div></div>`).join('')}</div></div>`;
}
async function loadCards(){
  setLoading('page-cards', true);
  try {
    const df=document.getElementById('cdDateFrom').value||''; const dt=document.getElementById('cdDateTo').value||''; const bank=document.getElementById('cdBank').value||'';
    const d=await j(`${API}/cards/daily?date_from=${encodeURIComponent(df)}&date_to=${encodeURIComponent(dt)}&bank=${encodeURIComponent(bank)}`).catch(()=>({cards:[]}));
    state.dailyCards=d.cards||[];
    const wrap=document.getElementById('cardsDailyWrap');
    wrap.innerHTML=(state.dailyCards||[]).length?state.dailyCards.map(cardHtml).join(''):'<div class="card"><div class="muted">Sem cards para o filtro selecionado.</div></div>';
  } finally {
    setLoading('page-cards', false);
  }
}
async function saveCardByKey(key){
  let meta={};
  try{ meta = JSON.parse(decodeURIComponent(escape(atob(key)))); }catch(e){ alert('Card inválido'); return; }
  const root=document.querySelector(`#cardsDailyWrap [data-card-key="${key}"]`);
  if(!root) return;
  const body={production_date:meta.production_date, bank:meta.bank, card_type:meta.card_type, tag:meta.tag||'', instrument:meta.instrument||'', title:meta.title||'', flow_velocity_ms:null, dp_value:null, observations:''};
  root.querySelectorAll('input[data-field],textarea[data-field]').forEach(el=>{ body[el.dataset.field]=el.value===''?null:el.value; });
  await j(`${API}/cards/upsert`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).catch(()=>null);
  loadCards();
}
async function deleteCard(id) {
  if (!confirm('Excluir card/ajuste?')) return;
  try {
    const res = await fetch(`${API}/cards/${id}`, {method:'DELETE'});
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}));
      throw new Error(payload.detail || payload.error || `Falha HTTP ${res.status}`);
    }
    loadCards();
  } catch(err) {
    alert(`Erro ao excluir card: ${err.message}`);
  }
}
async function newManualCard(){
  const production_date=document.getElementById('cdDateTo').value||document.getElementById('cdDateFrom').value; const bank=document.getElementById('cdBank').value||prompt('Banco (B03/B05/B08/B10):','B10')||'';
  if(!production_date||!bank){ alert('Informe data e banco.'); return; }
  const title=prompt('Título do card manual:','Card Manual'); if(!title) return;
  const tag=prompt('TAG (opcional):','')||''; const instrument=prompt('Instrumento (opcional):','')||'';
  await j(`${API}/cards/manual`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({production_date,bank,tag,instrument,title,observations:''})});
  loadCards();
}

document.getElementById('btnLoadCards').onclick = loadCards;
document.getElementById('btnCardPdf').onclick = ()=>{ const df=document.getElementById('cdDateFrom').value||''; const dt=document.getElementById('cdDateTo').value||''; const bank=document.getElementById('cdBank').value||''; window.open(`${API}/cards/export-pdf?date_from=${encodeURIComponent(df)}&date_to=${encodeURIComponent(dt)}&bank=${encodeURIComponent(bank)}`); };
document.getElementById('btnNewManualCard').onclick = newManualCard;
