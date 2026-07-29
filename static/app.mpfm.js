'use strict';

// ── DADOS MPFM (com colunas configuráveis) ────────────────────────────────────
async function loadPrefs() {
  const d = await j(`${API}/user-prefs`).catch(() => ({prefs:{selected_metrics:[]}, all_metrics:[]}));
  state.prefs = d.prefs || {};
  state.allMetrics = d.all_metrics || [];
  state.selectedCols = state.prefs.selected_metrics || [];
  if (typeof applyThemePreference === 'function') applyThemePreference(state.prefs.theme_mode);
  buildColCheckGrid();
}

function buildColCheckGrid() {
  const GROUPS = {
    prod:['MPFM corr Óleo (t)','MPFM corr Gás (t)','MPFM corr HC (t)','MPFM corr Água (t)','MPFM corr Total (t)'],
    pvt: ['PVT vol Óleo (m³)','PVT vol Gás (sm³)','PVT vol Água (m³)','PVT @20 vol Óleo (m³)','PVT @20 vol Gás (sm³)'],
    fwa: ['Pressão (barg)','Temperatura (°c)','Dens. Gás (kg/m³)','Dens. Óleo (kg/m³)','Dens. Água (kg/m³)'],
  };
  document.getElementById('colCheckGrid').innerHTML = state.allMetrics.map(m => {
    const on = state.selectedCols.includes(m);
    const grp = Object.entries(GROUPS).find(([,cols]) => cols.includes(m));
    const dot = grp ? {prod:'#26a0ff',pvt:'#f3b33d',fwa:'#23c16b'}[grp[0]] : '#8ea3ba';
    return `<label class="chk-item ${on?'on':''}" id="chk_${CSS.escape(m)}" onclick="toggleCol(this,'${escapeHtml(m).replace(/'/g,'\\\'')}')" >
      <input type="checkbox" ${on?'checked':''} style="accent-color:${dot}" onclick="event.stopPropagation()">
      <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${dot};flex-shrink:0"></span>
      ${escapeHtml(m)}</label>`;
  }).join('');
}
window.toggleCol = (lbl, metric) => {
  const cb = lbl.querySelector('input');
  cb.checked = !cb.checked;
  lbl.classList.toggle('on', cb.checked);
  if (cb.checked && !state.selectedCols.includes(metric)) state.selectedCols.push(metric);
  else state.selectedCols = state.selectedCols.filter(x => x !== metric);
};
window.colSelectGroup = group => {
  const G = {prod:['MPFM corr Óleo (t)','MPFM corr Gás (t)','MPFM corr HC (t)','MPFM corr Água (t)','MPFM corr Total (t)'],
              pvt:['PVT mass Óleo (t)','PVT mass Gás (t)','PVT vol Óleo (m³)','PVT vol Gás (sm³)','PVT @20 mass Óleo (t)','PVT @20 mass Gás (t)'],
              fwa:['Pressão (barg)','Temperatura (°c)','Dens. Gás (kg/m³)','Dens. Óleo (kg/m³)','Dens. Água (kg/m³)'],
              all: state.allMetrics, none:[]};
  const sel = G[group] || [];
  state.selectedCols = [...sel];
  buildColCheckGrid();
};
window.saveColPrefs = async () => {
  const body = {...state.prefs, selected_metrics: state.selectedCols};
  await j(`${API}/user-prefs`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  document.getElementById('colSaveStatus').textContent = '✅ Salvo!';
  setTimeout(() => document.getElementById('colSaveStatus').textContent = '', 2000);
  document.getElementById('colModal').classList.remove('show');
  loadMPFM();
};

document.getElementById('btnColConfig').onclick = () => {
  buildColCheckGrid();
  document.getElementById('colModal').classList.add('show');
};
document.getElementById('closeColModal').onclick = () => document.getElementById('colModal').classList.remove('show');

async function loadMPFM(silent = false) {
  if (!silent) setLoading('page-mpfm', true);
  try {
  const qs = new URLSearchParams({
    date_from: document.getElementById('mDateFrom').value,
    date_to:   document.getElementById('mDateTo').value,
    row_kind:  document.getElementById('mKind').value,
    bank:      document.getElementById('mBank').value,
    tag:       document.getElementById('mTag').value || '',
    metric:    '',
    q:         document.getElementById('mQ').value,
  });
  const d = await j(`${API}/ops/mpfm-data?${qs}`);
  state.mpfmRows = d.rows || [];
  fillSelect('mBank', d.banks, true);
  fillSelect('mTag',  d.tags,  true);
  fillSelect('cBank', d.banks, true);
  renderMPFMContext();
  renderMPFM();
  } finally {
    if (!silent) setLoading('page-mpfm', false);
  }
}

function renderMPFMContext() {
  const host = document.getElementById('mpfmContext');
  if (!host) return;
  const rows = state.mpfmRows || [];
  const uniqueGroups = new Set(rows.map(r => `${r.day_ref}||${r.hour_ref ?? ''}||${r.bank}||${r.tag}`));
  const manualRows = rows.filter(r => r.source_kind === 'manual');
  const sourceFiles = [...new Set(rows.map(r => r.source_file).filter(Boolean))];
  host.innerHTML = `
    <div class="mpfm-context-card"><div class="k">Linhas carregadas</div><div class="v">${rows.length}</div><div class="m">métricas no recorte atual</div></div>
    <div class="mpfm-context-card"><div class="k">Registros pivotados</div><div class="v">${uniqueGroups.size}</div><div class="m">data + hora + banco + TAG</div></div>
    <div class="mpfm-context-card"><div class="k">Origem manual</div><div class="v">${manualRows.length}</div><div class="m">métricas inseridas ou ajustadas na aplicação</div></div>
    <div class="mpfm-context-card"><div class="k">Arquivos de origem</div><div class="v">${sourceFiles.length}</div><div class="m" title="${escapeHtml(sourceFiles.join('\n'))}">${escapeHtml(sourceFiles[0] || 'sem arquivo')}</div></div>
  `;
}

function renderMPFM() {
  const sel = state.selectedCols.length ? state.selectedCols : ['MPFM corr Óleo (t)','MPFM corr Gás (t)','MPFM corr HC (t)'];
  // Build pivot map keeping individual row IDs per metric
  const pivotMap = new Map();
  state.mpfmRows.forEach(r => {
    const key = `${r.day_ref}||${r.hour_ref??''}||${r.bank}||${r.tag}`;
    if (!pivotMap.has(key)) {
      pivotMap.set(key, {
        day_ref:r.day_ref,
        hour_ref:r.hour_ref,
        bank:r.bank,
        tag:r.tag,
        source_file:r.source_file || '',
        source_kind:r.source_kind || '',
        row_kind:r.row_kind || '',
        __rowKey:key,
      });
    }
    pivotMap.get(key)[r.metric_name] = r.metric_value;
    pivotMap.get(key)[`__id_${r.metric_name}`] = r.id;
  });
  const rows = [...pivotMap.values()];
  state.mpfmPivotRows = rows;
  document.getElementById('mpfmThead').innerHTML = `<tr>
    <th>Data</th><th>Hora</th><th>Banco</th><th>TAG</th><th>Origem</th>
    ${sel.map(m => `<th title="${escapeHtml(m)}">${escapeHtml(m.replace(/\s*\([^)]*\)/,'').trim())}</th>`).join('')}
    <th style="width:50px"></th>
  </tr>`;
  document.getElementById('mpfmRows').innerHTML = rows.map((r, ri) => `
    <tr id="mrow_${ri}">
      <td class="mono">${escapeHtml(fmtDate(r.day_ref))}</td>
      <td class="mono">${r.hour_ref==null?'—':String(r.hour_ref).padStart(2,'0')+':00'}</td>
      <td>${tagChip(r.bank||'')}</td>
      <td class="mono" style="font-size:12px">${escapeHtml(r.tag||'')}</td>
      <td><div class="mpfm-origin-cell"><span class="badge ${r.source_kind==='manual'?'warn':'ok'}">${r.source_kind==='manual'?'Manual':'Arquivo'}</span><div class="mpfm-origin-meta" title="${escapeHtml(r.source_file||'')}">${escapeHtml(r.source_file||'sem arquivo')}</div></div></td>
      ${sel.map(m => {
        const id = r[`__id_${m}`];
        const v  = r[m];
        return `<td class="num" id="mc_${id||'_'+ri+'_'+escapeHtml(m)}" style="cursor:${id?'pointer':'default'}"
          ${id ? `onclick="editMeasurement(${id}, this, '${jsStr(m)}', '${jsStr(r.day_ref)}', ${r.hour_ref??'null'}, '${jsStr(r.bank)}', 'mpfm')" title="Clique para editar"` : ''}>${fmt(v)}</td>`;
      }).join('')}
      <td style="text-align:center">
        <button class="btn danger sm" onclick="deleteMpfmRow(${ri})" title="Excluir linha do dia na base" aria-label="Excluir linha MPFM">Excluir</button>
      </td>
    </tr>`).join('') || `<tr><td colspan="${6+sel.length}" class="muted">Sem dados para os filtros.</td></tr>`;
}

window.deleteMpfmRow = async (ri) => {
  if (!confirm('Excluir todos os valores desta linha do banco de dados?')) return;
  const row = (state.mpfmPivotRows || [])[ri];
  const pivotKey = row ? row.__rowKey : '';
  const ids = [...new Set((state.mpfmRows || [])
    .filter(r => `${r.day_ref}||${r.hour_ref ?? ''}||${r.bank}||${r.tag}` === pivotKey)
    .map(r => r.id)
    .filter(Boolean))];
  await Promise.all(ids.map(id => j(`${API}/measurements/${id}`, {method:'DELETE'})));
  await loadMPFM();
  await notifyDataChanged(['mpfm','resumo','cards','monitoramento','xml042','exportar']);
};
document.getElementById('mLoad').onclick = loadMPFM;

// CSV + Excel export for MPFM
function mpfmExportQs() {
  return new URLSearchParams({
    date_from: document.getElementById('mDateFrom').value,
    date_to:   document.getElementById('mDateTo').value,
    row_kind:  document.getElementById('mKind').value,
    bank:      document.getElementById('mBank').value,
    metrics:   state.selectedCols.join(','),
  });
}
document.getElementById('btnExportCsv').onclick  = () => window.open(`${API}/export-csv?${mpfmExportQs()}`, '_blank');
document.getElementById('btnExportXlsx').onclick = () => window.open(`${API}/export-excel?${mpfmExportQs()}`, '_blank');

