'use strict';

const SEP_ALL_METRICS = [
  // Volumes
  { key:'oil_m3',        label:'Óleo (m³)',          group:'volumes',   color:'#23c16b' },
  { key:'gsv_sep_sm3',   label:'GSV óleo (sm³)',     group:'volumes',   color:'#23c16b' },
  { key:'gas_vol_sm3',   label:'Gás (sm³)',          group:'volumes',   color:'#f3b33d' },
  { key:'water_gsv_sm3', label:'GSV Água (m³)',       group:'volumes',   color:'#26a0ff' },
  // Massas
  { key:'oil_t',         label:'Óleo (t)',            group:'massas',    color:'#23c16b' },
  { key:'gas_t',         label:'Gás (t)',             group:'massas',    color:'#f3b33d' },
  { key:'water_t',       label:'Água (t)',            group:'massas',    color:'#26a0ff' },
  { key:'hc_t',          label:'HC (t)',              group:'massas',    color:'#26a0ff' },
  { key:'total_t',       label:'Total (t)',           group:'massas',    color:'#dbe7f5' },
  // Condições P/T
  { key:'temp',          label:'Temperatura (°c)',    group:'condicoes', color:'#ef5a5a' },
  { key:'pressure_barg', label:'Pressão (barg)',      group:'condicoes', color:'#a855f7' },
  { key:'density_sim',   label:'Dens. sim (kg/m³)',   group:'condicoes', color:'#8ea3ba' },
  { key:'bsw_user_pct',  label:'BSW usuário (%)',     group:'condicoes', color:'#8ea3ba' },
];

const SEP_METRIC_LABELS = Object.fromEntries(SEP_ALL_METRICS.map(m => [m.key, m.label]));
const SEP_FLUID_HEADER_LABELS = {
  Hour: 'Hora',
  Pressure_kPa: 'Pressão (kpa)',
  Pressure_barg: 'Pressão (barg)',
  Temperature_degC: 'Temperatura (deg c)',
  SD_kg_sm3: 'SD (kg/sm³)',
  MD_kg_m3: 'MD (kg/m³)',
  IV_m3: 'IV (m³)',
  GV_m3: 'GV (m³)',
  GSV_sm3: 'GSV (sm³)',
  Mass_ton: 'Massa (t)',
  NSV_sm3: 'NSV (sm³)',
  BSW_pct: 'BSW (%)',
  CPL: 'CPL',
  CTL: 'CTL',
  Pressure_kPa_g: 'Pressão (kpa_g)',
  DT_kg_m3: 'DT (kg/m³)',
  GrVol_m3: 'Gr. vol. (m³)',
  StVol_m3: 'St. vol. (m³)',
  Mass_t: 'Massa (t)',
  Energy_GJ: 'Energia (gj)',
  DiffPress_kPa: 'ΔP (kpa)',
  Flowtime_min: 'Flowtime (min)',
};

// Default selected columns
const SEP_DEFAULT_COLS = ['oil_t','gas_t','water_t','hc_t','total_t','temp','pressure_barg'];

async function loadSep(silent = false) {
  if (!silent) setLoading('page-separador', true);
  try {
    const dateFrom = document.getElementById('sDateFrom').value;
    const dateTo   = document.getElementById('sDateTo').value;
    const qs = new URLSearchParams({date_from:dateFrom, date_to:dateTo});
    const d = await j(`${API}/ops/sep-data?${qs}`);
    document.getElementById('sepDays').innerHTML = (d.days||[]).map(r =>
      `<tr><td class="mono">${escapeHtml(fmtDate(r.content_date))}</td><td>${r.oleo?'✅':'—'}</td><td>${r.agua?'✅':'—'}</td><td>${r.gas?'✅':'—'}</td><td>${r.aligned_banks?tagChip(r.aligned_banks):(r.recovered_from_excel?'<span class="muted">Reconstituído</span>':'<span class="muted">Extraído</span>')}</td><td>${badge(r.status)} ${r.recovered_from_excel?'<span class="badge info">Recuperado do Excel</span>':''} <span class="muted" style="font-size:11px">${escapeHtml(r.status_label||'')}</span></td></tr>`
    ).join('') || '<tr><td colspan="6" class="muted">Sem dados do separador.</td></tr>';
    document.getElementById('sepRows').innerHTML = (d.rows||[]).map(r =>
      `<tr><td>${escapeHtml(r.content_date||'')}</td><td>${r.recovered_from_excel?'<span class="badge info">Recuperado do Excel</span>':escapeHtml(r.file_type||'')}</td><td>${escapeHtml(r.meter_id||'')}</td><td title="${escapeHtml(r.message||'')}">${escapeHtml(r.location||'')}</td><td>${r.aligned_banks?tagChip(r.aligned_banks):(r.recovered_from_excel?'<span class="muted">Reconstituído</span>':'<span class="muted">Extraído</span>')}</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis" title="${escapeHtml(r.filename||'')}">${escapeHtml(r.filename||'')}</td></tr>`
    ).join('') || '<tr><td colspan="6" class="muted">Sem arquivos do separador.</td></tr>';
    await Promise.all([
      loadSepData(dateFrom, dateTo),
      loadSepAlignments(dateFrom, dateTo, ''),
      loadSepDuplicates(dateFrom, dateTo),
      loadSepFluidTables(dateFrom, dateTo)
    ]);
  } finally {
    if (!silent) setLoading('page-separador', false);
  }
}
document.getElementById('sLoad').onclick = loadSep;

// Auto-populate sep date range on page load
async function autoSetSepDates() {
  const month = document.getElementById('globalMonth')?.value || '';
  if (!month) return;
  const {from, to} = getMonthRange(month);
  document.getElementById('sDateFrom').value = from;
  document.getElementById('sDateTo').value = to;
  const sa = document.getElementById('saDate'); if (sa && !sa.value) sa.value = from;
  if (typeof refreshDateInputDisplay === 'function') refreshDateInputDisplay(document);
}

async function loadSepData(overrideDateFrom, overrideDateTo) {
  const dateFrom = overrideDateFrom || document.getElementById('sDateFrom').value || '';
  const dateTo   = overrideDateTo   || document.getElementById('sDateTo').value   || '';
  const unit     = document.getElementById('sUnit')?.value || '';
  const qs = new URLSearchParams();
  if (dateFrom) qs.set('date_from', dateFrom);
  if (dateTo)   qs.set('date_to',   dateTo);
  if (unit)     qs.set('unit',      unit);
  const d = await j(`${API}/sep/data?${qs}`).catch(e => { console.error('loadSepData error:', e); return {rows:[], metric_cols:[]}; });
  state.sepAllDbCols = d.metric_cols || [];
  state.sepRows = d.rows || [];
  // Bootstrap selected cols on first load
  if (!state.sepSelectedCols || state.sepSelectedCols.length === 0) {
    const prefs = await j(`${API}/user-prefs`).catch(() => ({}));
    const saved = prefs?.prefs?.sep_selected_metrics;
    state.sepSelectedCols = (saved && saved.length) ? saved :
      (state.sepAllDbCols.length ? state.sepAllDbCols : [...SEP_DEFAULT_COLS]);
  }
  renderSepData();
}


function switchSepFluidTab(fluid){
  state.sepActiveFluid = fluid;
  document.querySelectorAll('.sep-tab').forEach(el=>el.classList.toggle('active', el.dataset.fluidTab===fluid));
  document.querySelectorAll('.fluid-pane').forEach(el=>el.classList.toggle('active', el.id===`fluidPane_${fluid}`));
}
window.switchSepFluidTab = switchSepFluidTab;

function sepFluidLabel(fluid){ return ({oleo:'Óleo', gas:'Gás', agua:'Água'})[fluid] || fluid; }
function classifySepHeader(h){
  const k = String(h||'').toLowerCase();
  if (k.includes('pressure')) return 'grp-pressure';
  if (k.includes('temp')) return 'grp-temp';
  if (k.includes('sd_') || k.includes('md_') || k.includes('dt_')) return 'grp-density';
  if (k.includes('iv_') || k.includes('gv_') || k.includes('gsv_') || k.includes('nsv_') || k.includes('grvol') || k.includes('stvol')) return 'grp-volume';
  if (k.includes('cpl') || k.includes('ctl') || k.includes('bsw') || k.includes('flowtime')) return 'grp-factor';
  if (k.includes('energy')) return 'grp-energy';
  return '';
}
function renderSepFluidSummary(){
  const host = document.getElementById('sepFluidSummary');
  const fluids = ['oleo','gas','agua'];
  host.innerHTML = fluids.map(f=>{
    const m = state.sepFluidMeta[f] || {};
    const sourceKind = m.source_kind === 'manual' ? 'Manual' : m.source_file ? 'TXT oficial' : 'Sem origem';
    return `<div class="fluid-card">
      <div class="top"><div class="name">${sepFluidLabel(f)}</div><span class="badge ${m.rows?'info':'muted-badge'}">${m.rows||0} linhas</span></div>
      <div class="meta">
        <div>TAG do medidor<strong>${escapeHtml(m.tag || '—')}</strong></div>
        <div>Meter ID<strong>${escapeHtml(m.instrument || '—')}</strong></div>
        <div>Período<strong>${(m.date_from&&m.date_to)?`${escapeHtml(fmtDate(m.date_from))} → ${escapeHtml(fmtDate(m.date_to))}`:'—'}</strong></div>
        <div>Colunas<strong>${m.headers_count || 0}</strong></div>
        <div>Origem<strong>${escapeHtml(sourceKind)}</strong></div>
        <div>Fonte<strong title="${escapeHtml(m.source_file || '')}">${escapeHtml(m.source_file || '—')}</strong></div>${m.fallback_used?`<div>Período<strong>Último dia disponível</strong></div>`:''}
      </div>
    </div>`;
  }).join('');
}

async function loadSepFluidTable(fluid, headId, bodyId, dateFrom, dateTo) {
  const qs = new URLSearchParams();
  if (dateFrom) qs.set('date_from', dateFrom);
  if (dateTo) qs.set('date_to', dateTo);
  qs.set('fluid', fluid);
  const d = await j(`${API}/sep/fluid-data?${qs}`).catch(() => ({headers:[], rows:[]}));
  const headers = d.headers || [];
  const rows = d.rows || [];
  state.sepFluidRows[fluid] = rows;
  state.sepFluidMeta[fluid] = {
    rows: rows.length,
    headers_count: headers.length,
    tag: rows[0]?.tag || '',
    instrument: rows[0]?.instrument || '',
    source_file: rows[0]?.source_file || '',
    source_kind: rows[0]?.source_kind || '',
    date_from: d.date_from || dateFrom || '',
    date_to: d.date_to || dateTo || '',
    fallback_used: !!d.fallback_used,
    latest_available: d.latest_available || ''
  };
  renderSepFluidSummary();
  const host = document.getElementById(bodyId)?.closest('.tablewrap')?.parentElement;
  if (host) {
    const first = rows[0] || {};
    const allDates = [...new Set(rows.map(r => r.day_ref).filter(Boolean))];
    host.querySelector('.sep-context')?.remove();
    const ctx = document.createElement('div');
    ctx.className = 'sep-context';
    const sourceLabel = first.source_kind === 'manual' ? 'Manual' : first.source_file ? 'TXT oficial' : '—';
    ctx.innerHTML = `
      <div class="ctx"><div class="k">Data</div><div class="v">${allDates.length===1?escapeHtml(fmtDate(allDates[0])):allDates.length?`${escapeHtml(fmtDate(allDates[0]))} …`:'—'}</div></div>
      <div class="ctx"><div class="k">TAG do medidor</div><div class="v">${escapeHtml(first.tag || '—')}</div></div>
      <div class="ctx"><div class="k">Meter ID</div><div class="v">${escapeHtml(first.instrument || '—')}</div></div>
      <div class="ctx"><div class="k">Linhas</div><div class="v">${rows.length}</div></div>
      <div class="ctx"><div class="k">Origem</div><div class="v">${escapeHtml(sourceLabel)}</div></div>
      <div class="ctx"><div class="k">Fonte</div><div class="v" title="${escapeHtml(first.source_file || '')}">${escapeHtml(first.source_file || '—')}</div></div>`;
    host.insertBefore(ctx, host.querySelector('.tablewrap'));
  }
  document.getElementById(headId).innerHTML = `<tr>${headers.map(h=>`<th class="${classifySepHeader(h)}">${escapeHtml(SEP_FLUID_HEADER_LABELS[h] || h)}</th>`).join('')}<th>Ações</th></tr>`;
  document.getElementById(bodyId).innerHTML = rows.map((r, idx) => `<tr>
    ${headers.map(h=>`<td class="${h==='Hour'?'mono':''}">${r[h]!=null?(h==='Hour'?(r[h]==='DAY'?'<span style="color:var(--muted)">DAY</span>':escapeHtml(r[h])):(typeof r[h]==='number'?fmt(r[h]):escapeHtml(r[h]))):'—'}</td>`).join('')}
    <td style="white-space:nowrap"><button class="btn secondary sm" onclick="editSepFluidRow('${fluid}', ${idx})">Editar</button> <button class="btn danger sm" onclick="deleteSepFluidRow('${fluid}', ${idx})">Excluir</button></td>
  </tr>`).join('') || `<tr><td colspan="${headers.length+1}" class="muted" style="padding:16px;text-align:center">Sem dados para o período selecionado.</td></tr>`;
}

async function saveSepFluidRow(fluid, payload){
  await j(`${API}/sep/fluid-row`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  await loadSepFluidTables(document.getElementById('sDateFrom').value, document.getElementById('sDateTo').value);
}
window.deleteSepFluidRow = async (fluid, idx) => {
  const row = (state.sepFluidRows[fluid]||[])[idx]; if(!row) return;
  if(!confirm(`Excluir linha ${row.Hour==='DAY'?'DAY':row.Hour} de ${sepFluidLabel(fluid)}?`)) return;
  await j(`${API}/sep/fluid-row`, {method:'DELETE', headers:{'Content-Type':'application/json'}, body: JSON.stringify({fluid, day_ref: row.day_ref, hour_ref: row.hour_ref, tag: row.tag})});
  await loadSepFluidTables(document.getElementById('sDateFrom').value, document.getElementById('sDateTo').value);
};
window.editSepFluidRow = async (fluid, idx) => {
  const row = (state.sepFluidRows[fluid]||[])[idx]; if(!row) return;
  const headers = (fluid==='oleo' || fluid==='agua') ? ['Pressure_kPa','Pressure_barg','Temperature_degC','SD_kg_sm3','MD_kg_m3','IV_m3','GV_m3','GSV_sm3','Mass_ton','NSV_sm3','BSW_pct','CPL','CTL'] : ['Pressure_kPa_g','Temperature_degC','SD_kg_sm3','DT_kg_m3','GrVol_m3','StVol_m3','Mass_t','Energy_GJ','DiffPress_kPa','Flowtime_min'];
  const values = {};
  const day_ref = prompt('Data de produção (AAAA-MM-DD):', row.day_ref || ''); if(day_ref===null) return;
  const hourTxt = prompt('Hora (0-23) ou DAY:', row.Hour==='DAY' ? 'DAY' : String(row.Hour)); if(hourTxt===null) return;
  const tag = prompt('TAG do medidor:', row.tag || ''); if(tag===null || !tag.trim()) return;
  const instrument = prompt('Meter ID:', row.instrument || '') ?? '';
  for (const h of headers){
    if (fluid==='agua' && h==='Pressure_barg') continue;
    const cur = row[h] == null ? '' : row[h];
    const v = prompt(`${SEP_FLUID_HEADER_LABELS[h] || h}:`, cur);
    if (v===null) return;
    values[h] = v;
  }
  await saveSepFluidRow(fluid, {fluid, day_ref: day_ref.trim(), hour_ref: hourTxt.trim().toUpperCase()==='DAY'?null:hourTxt.trim(), tag: tag.trim(), instrument: instrument.trim(), values});
};
window.addSepFluidRow = async (fluid) => {
  const day_ref = prompt('Data de produção (AAAA-MM-DD):', document.getElementById('sDateFrom').value || ''); if(day_ref===null || !day_ref.trim()) return;
  const hourTxt = prompt('Hora (0-23) ou DAY:', 'DAY'); if(hourTxt===null) return;
  const tag = prompt('TAG do medidor:', ''); if(tag===null || !tag.trim()) return;
  const instrument = prompt('Meter ID:', '') ?? '';
  const headers = (fluid==='oleo' || fluid==='agua') ? ['Pressure_kPa','Pressure_barg','Temperature_degC','SD_kg_sm3','MD_kg_m3','IV_m3','GV_m3','GSV_sm3','Mass_ton','NSV_sm3','BSW_pct','CPL','CTL'] : ['Pressure_kPa_g','Temperature_degC','SD_kg_sm3','DT_kg_m3','GrVol_m3','StVol_m3','Mass_t','Energy_GJ','DiffPress_kPa','Flowtime_min'];
  const values = {};
  for (const h of headers){
    if (fluid==='agua' && h==='Pressure_barg') continue;
    const v = prompt(`${SEP_FLUID_HEADER_LABELS[h] || h}:`, ''); if(v===null) return; values[h]=v;
  }
  await saveSepFluidRow(fluid, {fluid, day_ref: day_ref.trim(), hour_ref: hourTxt.trim().toUpperCase()==='DAY'?null:hourTxt.trim(), tag: tag.trim(), instrument: instrument.trim(), values});
};

async function loadSepFluidTables(dateFrom, dateTo) {
  await Promise.all([
    loadSepFluidTable('oleo','sepOilHead','sepOilRows', dateFrom, dateTo),
    loadSepFluidTable('gas','sepGasHead','sepGasRows', dateFrom, dateTo),
    loadSepFluidTable('agua','sepWaterHead','sepWaterRows', dateFrom, dateTo),
  ]);
  renderSepFluidSummary();
}

function renderSepData() {
  const rows = state.sepRows || [];
  const sel  = state.sepSelectedCols.length ? state.sepSelectedCols : SEP_DEFAULT_COLS;
  const q = (document.getElementById('sepSearch')?.value || '').toLowerCase().trim();
  const visible = q ? rows.filter(r =>
    (r.day_ref||'').includes(q) || (r.bank||'').toLowerCase().includes(q) || ((r.tag||'').toLowerCase().includes(q)) || ((r.aligned_banks||'').toLowerCase().includes(q)) || ((r.source||'').toLowerCase().includes(q)) || ((r.source_label||'').toLowerCase().includes(q)) ||
    sel.some(m => r[m] != null && String(r[m]).includes(q))
  ) : rows;

  document.getElementById('sepDataHead').innerHTML = `<tr>
    <th>Data</th><th>Hora</th><th>Origem</th><th>TAG SEP</th><th>Uso</th>
    ${sel.map(m => {
      const def = SEP_ALL_METRICS.find(x => x.key===m);
      return `<th style="color:${def?.color||'#8ea3ba'}" title="${escapeHtml(def?.group||'')}">${escapeHtml(def?.label||SEP_METRIC_LABELS[m]||m)}</th>`;
    }).join('')}
    <th style="width:60px"></th>
  </tr>`;

  document.getElementById('sepDataRows').innerHTML = visible.map((r, ri) => `
    <tr id="seprow_${ri}">
      <td class="mono">${escapeHtml(fmtDate(r.day_ref))}</td>
      <td class="mono" style="font-size:11px">${r.hour_ref==null?'<span style="color:var(--muted)">DAY</span>':escapeHtml(String(r.hour_ref).padStart(2,'0')+':00')}</td>
      <td><div class="sep-origin-cell"><span class="badge ${r.source_kind==='manual'?'warn':'ok'}">${escapeHtml(r.source_label || (r.source_kind==='manual'?'Manual':'TXT oficial'))}</span><div class="sep-origin-meta" title="${escapeHtml(r.source || '')}">${escapeHtml(r.source || 'sem arquivo')}</div></div></td>
      <td>${r.tag?tagChip(escapeHtml(r.tag)):'<span class="muted">—</span>'}</td>
      <td><div class="sep-usage-cell">${r.aligned_banks?tagChip(escapeHtml(r.aligned_banks)):'<span class="muted">Extraído</span>'}<div class="sep-origin-meta">${r.sep_status==='aplicado'?'em uso na aplicação':'aguardando alinhamento'}</div></div></td>
      ${sel.map(m => {
        const id   = r['__id_'+m];
        const v    = r[m];
        const def  = SEP_ALL_METRICS.find(x => x.key===m);
        const col  = def?.color||'var(--text)';
        return `<td class="num" id="sc_${id||'_'+ri+'_'+m}"
          style="cursor:pointer;color:${v!=null?col:'var(--line)'}"
          onclick="editMeasurement(${id||'null'},this,'${jsStr(m)}','${jsStr(r.day_ref)}',${r.hour_ref??'null'},'${jsStr(r.bank)}','sep')"
          title="${v!=null?escapeHtml((def?.label||m)+': '+v):'Sem dado — clique para inserir'}"
        >${v!=null?fmt(v):'—'}</td>`;
      }).join('')}
      <td style="text-align:center">
        <button class="btn danger sm" onclick="deleteSepRow(${ri})" title="Excluir linha do dia na base" aria-label="Excluir linha do separador">Excluir</button>
      </td>
    </tr>`).join('') ||
    `<tr><td colspan="${6+sel.length}" class="muted" style="padding:16px;text-align:center">Sem dados extraídos do separador para o período.</td></tr>`;
  state.sepCols = sel;
}

window.deleteSepRow = async (ri) => {
  if (!confirm('Excluir todos os valores desta linha do banco de dados?')) return;
  const r = state.sepRows[ri];
  if (!r) return;
  const allCols = [...new Set([...(state.sepSelectedCols||[]),...(state.sepAllDbCols||[])])];
  const ids = allCols.map(m => r['__id_'+m]).filter(x => x != null);
  if (ids.length) await Promise.all(ids.map(id => j(`${API}/measurements/${id}`, {method:'DELETE'})));
  else {
    state.sepRows.splice(ri,1);
    renderSepData();
    await notifyDataChanged(['separador','resumo','alertas','cards','exportar']);
    return;
  }
  await loadSepData(document.getElementById('sDateFrom').value, document.getElementById('sDateTo').value);
  await notifyDataChanged(['separador','resumo','alertas','cards','exportar']);
};

window.addSepRow = () => {
  const day  = document.getElementById('sDateFrom').value;
  const sel  = state.sepSelectedCols.length ? state.sepSelectedCols : SEP_DEFAULT_COLS;
  const tbody = document.getElementById('sepDataRows');
  const S = 'background:var(--bg);border:1px solid var(--accent);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px';
    const tr = document.createElement('tr');
    tr.innerHTML = `
    <td><input type="date" id="newSepDate" value="${escapeHtml(day)}" style="${S}"></td>
      <td><input type="number" id="newSepHour" placeholder="h 0-23" min="0" max="23" style="width:58px;${S}"></td>
    <td><input id="newSepUnit" value="SEP" aria-label="Origem do separador" readonly style="width:88px;${S}"></td>
      ${sel.map(m => { const def=SEP_ALL_METRICS.find(x=>x.key===m);
        return `<td><input type="number" step="any" id="newSep_${m}" placeholder="${escapeHtml(def?.label||m)}" title="${escapeHtml(def?.label||m)}" style="width:78px;${S}"></td>`;
      }).join('')}
    <td style="text-align:center;white-space:nowrap">
      <button class="btn sm" style="padding:4px 8px" onclick="saveSepNewRow(this)">✓ Ok</button>
      <button class="btn secondary sm" style="padding:4px 8px;margin-top:3px" onclick="this.closest('tr').remove()">✕</button>
    </td>`;
  tbody.prepend(tr);
  tr.querySelector('#newSepDate')?.focus();
};

  window.saveSepNewRow = async (btn) => {
    const tr   = btn.closest('tr');
    const day  = tr.querySelector('#newSepDate')?.value;
    const hour = tr.querySelector('#newSepHour')?.value;
    const unit = tr.querySelector('#newSepUnit')?.value;
    if (!day||!unit) { alert('Preencha a data e a origem do separador.'); return; }
  const sel = state.sepSelectedCols.length ? state.sepSelectedCols : SEP_DEFAULT_COLS;
  let saved = 0;
  for (const m of sel) {
    const val = tr.querySelector(`#newSep_${m}`)?.value;
    if (!val||val.trim()==='') continue;
    await j(`${API}/measurements`, {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({day_ref:day, hour_ref:hour?parseInt(hour):null, bank:'SEP',
          row_kind:'sep', metric_name:m, metric_value:parseFloat(val), tag:'SEP'})});
    saved++;
  }
  if (!saved) { alert('Nenhum valor preenchido.'); return; }
  await loadSepData(document.getElementById('sDateFrom').value, document.getElementById('sDateTo').value);
};


async function loadSepDuplicates(dateFrom, dateTo) {
  const qs = new URLSearchParams();
  if (dateFrom) qs.set('date_from', dateFrom);
  if (dateTo) qs.set('date_to', dateTo);
  const d = await j(`${API}/duplicates/sep?${qs}`).catch(()=>({rows:[]}));
  const tbody = document.getElementById('sepDupRows');
  tbody.innerHTML = (d.rows||[]).map(g => {
    const official = (g.items||[]).find(x => x.is_official);
    const opts = (g.items||[]).map(x => `<option value="${x.id}" ${x.is_official?'selected':''}>${escapeHtml(x.source_file)} [${escapeHtml(x.report_kind)}]</option>`).join('');
    return `<tr>
      <td class="mono">${escapeHtml(fmtDate(g.production_date))}</td>
      <td>${tagChip(escapeHtml(g.fluid_kind.replace('sep_','')))}</td>
      <td>${escapeHtml(g.meter_id||'—')}</td>
      <td>${g.candidates}</td>
      <td>${official ? escapeHtml(official.source_file) : '<span class="muted">pendente</span>'}</td>
      <td>
        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
          <select id="dupSel_${g.production_date}_${g.fluid_kind}_${g.meter_id}" style="max-width:240px;background:var(--panel2);border:1px solid var(--line);color:var(--text);padding:6px 8px;border-radius:8px">${opts}</select>
          <button class="btn secondary sm" onclick="resolveSepDuplicate('${g.production_date}','${g.fluid_kind}','${g.meter_id}','use')">Usar</button>
          <button class="btn secondary sm" onclick="resolveSepDuplicate('${g.production_date}','${g.fluid_kind}','${g.meter_id}','pending')">Pendente</button>
        </div>
      </td>
    </tr>`;
  }).join('') || '<tr><td colspan="6" class="muted" style="padding:16px;text-align:center">Sem duplicidades no período.</td></tr>';
}

async function resolveSepDuplicate(production_date, fluid_kind, meter_id, action) {
  const sel = document.getElementById(`dupSel_${production_date}_${fluid_kind}_${meter_id}`);
  const official_id = sel ? parseInt(sel.value||'0') : null;
  await j(`${API}/duplicates/sep/resolve`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({production_date, fluid_kind, meter_id, action, official_id})});
  await loadSep();
}

async function loadSepAlignments(dateFrom, dateTo, bank) {
  const qs = new URLSearchParams();
  if (dateFrom) qs.set('date_from', dateFrom);
  if (dateTo) qs.set('date_to', dateTo);
  if (bank) qs.set('bank', bank);
  const d = await j(`${API}/sep-alignments?${qs}`).catch(() => ({rows:[]}));
  document.getElementById('sepAlignRows').innerHTML = (d.rows||[]).map(r => `
    <tr>
      <td class="mono">${escapeHtml(fmtDate(r.production_date))}</td>
      <td>${tagChip(escapeHtml(r.bank))}</td>
      <td>${escapeHtml(r.mpfm_tag)||'<span class="muted">—</span>'}</td>
      <td>${escapeHtml(r.sep_meter_id)||'<span class="muted">—</span>'}</td>
      <td>${escapeHtml(r.sep_tag)||'<span class="muted">—</span>'}</td>
      <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis">${escapeHtml(r.notes||'')}</td>
      <td style="text-align:center"><button class="btn danger sm" onclick="deleteSepAlignment(${r.id})">✕</button></td>
    </tr>
  `).join('') || '<tr><td colspan="7" class="muted" style="padding:16px;text-align:center">Sem alinhamentos ativos no período.</td></tr>';
}

document.getElementById('btnSaveSepAlignment').onclick = async () => {
  const body = {
    production_date: document.getElementById('saDate').value || document.getElementById('sDateFrom').value,
    bank: document.getElementById('saBank').value,
    mpfm_tag: document.getElementById('saMpfmTag').value.trim(),
    sep_meter_id: document.getElementById('saMeterId').value.trim(),
    sep_tag: document.getElementById('saSepTag').value.trim() || 'SEP',
    notes: document.getElementById('saNotes').value.trim(),
  };
  if (!body.production_date || !body.bank) { alert('Informe a data de produção e o banco.'); return; }
  await j(`${API}/sep-alignments`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  await loadSep();
};

window.deleteSepAlignment = async (id) => {
  if (!confirm('Excluir este alinhamento ativo?')) return;
  await j(`${API}/sep-alignments/${id}`, {method:'DELETE'});
  await loadSep();
};

// ── SEP COLUMN PICKER ─────────────────────────────────────────────────────────
function buildSepColCheckGrid() {
  const GL = {volumes:'📦 Volumes', massas:'⚖ Massas', condicoes:'🌡 Cond. P/T'};
  const byGroup = {};
  SEP_ALL_METRICS.forEach(m => { (byGroup[m.group]||(byGroup[m.group]=[])).push(m); });
  let inner = '';
  for (const [grp, mets] of Object.entries(byGroup)) {
    inner += `<div style="grid-column:1/-1;margin:8px 0 4px;font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em">${GL[grp]||grp}</div>`;
    inner += mets.map(m => {
      const on = state.sepSelectedCols.includes(m.key);
      return `<label class="chk-item ${on?'on':''}" onclick="toggleSepCol(this,'${m.key}')">
        <input type="checkbox" ${on?'checked':''} style="accent-color:${m.color}" onclick="event.stopPropagation()">
        <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${m.color};flex-shrink:0"></span>
        ${m.label}</label>`;
    }).join('');
  }
  document.getElementById('sepColCheckGrid').innerHTML = inner;
}
window.toggleSepCol = (lbl, key) => {
  const cb = lbl.querySelector('input'); cb.checked = !cb.checked;
  lbl.classList.toggle('on', cb.checked);
  if (cb.checked && !state.sepSelectedCols.includes(key)) state.sepSelectedCols.push(key);
  else state.sepSelectedCols = state.sepSelectedCols.filter(x=>x!==key);
};
window.sepColSelectGroup = grp => {
  const G = {
    volumes:   SEP_ALL_METRICS.filter(m=>m.group==='volumes').map(m=>m.key),
    massas:    SEP_ALL_METRICS.filter(m=>m.group==='massas').map(m=>m.key),
    condicoes: SEP_ALL_METRICS.filter(m=>m.group==='condicoes').map(m=>m.key),
    all: SEP_ALL_METRICS.map(m=>m.key), none:[],
  };
  state.sepSelectedCols = [...(G[grp]||[])];
  buildSepColCheckGrid();
};
window.saveSepColPrefs = async () => {
  const ex = await j(`${API}/user-prefs`).catch(()=>({prefs:{}}));
  await j(`${API}/user-prefs`,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({...(ex?.prefs||{}), sep_selected_metrics: state.sepSelectedCols})});
  const st = document.getElementById('sepColSaveStatus');
  st.textContent='✅ Salvo!'; setTimeout(()=>st.textContent='',2500);
  document.getElementById('sepColModal').classList.remove('show');
  renderSepData();
};
document.getElementById('btnSepColConfig').onclick = () => { buildSepColCheckGrid(); document.getElementById('sepColModal').classList.add('show'); };
document.getElementById('closeSepColModal').onclick = () => document.getElementById('sepColModal').classList.remove('show');

function sepExportQs() {
  const qs = new URLSearchParams();
  const from = document.getElementById('sDateFrom').value;
  const to   = document.getElementById('sDateTo').value;
  const sourceUnit = document.getElementById('sUnit')?.value || '';
  if (from) qs.set('date_from', from);
  if (to)   qs.set('date_to',   to);
  if (sourceUnit) qs.set('unit', sourceUnit);
  return qs;
}
function prodExportQs() {
  const qs = new URLSearchParams();
  const from = document.getElementById('sDateFrom').value;
  const to   = document.getElementById('sDateTo').value;
  const checkedOrDefault = (id, fallback = true) => {
    const el = document.getElementById(id);
    return el ? !!el.checked : fallback;
  };
  if (from) qs.set('date_from', from);
  if (to)   qs.set('date_to',   to);
  qs.set('include_daily', checkedOrDefault('exDaily') ? '1' : '0');
  qs.set('include_hourly', checkedOrDefault('exHourly') ? '1' : '0');
  qs.set('include_sep_oil', checkedOrDefault('exSepOil') ? '1' : '0');
  qs.set('include_sep_gas', checkedOrDefault('exSepGas') ? '1' : '0');
  qs.set('include_sep_water', checkedOrDefault('exSepWater') ? '1' : '0');
  return qs;
}
document.getElementById('btnExportSepCsv').onclick  = () => window.open(`${API}/export-sep-csv?${sepExportQs()}`, '_blank');
document.getElementById('btnExportSepXlsx').onclick = () => window.open(`${API}/export-sep-excel?${sepExportQs()}`, '_blank');
document.getElementById('btnExportProdXlsx').onclick = () => window.open(`${API}/export-producao-excel?${prodExportQs()}`, '_blank');
