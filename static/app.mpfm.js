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
  const adjustedRows = rows.filter(r => r.is_adjusted || r.source_kind === 'ajustado');
  const sourceFiles = [...new Set(rows.map(r => r.source_file).filter(Boolean))];
  host.innerHTML = `
    <div class="mpfm-context-card"><div class="k">Linhas carregadas</div><div class="v">${rows.length}</div><div class="m">métricas no recorte atual</div></div>
    <div class="mpfm-context-card"><div class="k">Registros pivotados</div><div class="v">${uniqueGroups.size}</div><div class="m">data + hora + banco + TAG</div></div>
    <div class="mpfm-context-card"><div class="k">Dados corrigidos</div><div class="v">${adjustedRows.length}</div><div class="m">métricas alteradas por registro de ajustes</div></div>
    <div class="mpfm-context-card"><div class="k">Arquivos de origem</div><div class="v">${sourceFiles.length}</div><div class="m" title="${escapeHtml(sourceFiles.join('\n'))}">${escapeHtml(sourceFiles[0] || 'sem arquivo')}</div></div>
  `;
}

function mpfmSourceBadge(kind, adjusted) {
  if (adjusted || kind === 'ajustado') return '<span class="badge adjusted">Corrigido</span>';
  if (kind === 'manual') return '<span class="badge warn">Manual</span>';
  return '<span class="badge ok">Arquivo</span>';
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
        is_adjusted:Boolean(r.is_adjusted),
        adjustment_source:r.adjustment_source || '',
        row_kind:r.row_kind || '',
        __rowKey:key,
        __adjusted_metrics:new Set(),
      });
    }
    const target = pivotMap.get(key);
    target[r.metric_name] = r.metric_value;
    target[`__id_${r.metric_name}`] = r.id;
    target[`__source_${r.metric_name}`] = r.source_file || '';
    target[`__adjustment_source_${r.metric_name}`] = r.adjustment_source || '';
    if (r.is_adjusted || r.source_kind === 'ajustado') {
      target.is_adjusted = true;
      target.source_kind = 'ajustado';
      target.source_file = r.source_file || target.source_file;
      target.adjustment_source = r.adjustment_source || target.adjustment_source;
      target.__adjusted_metrics.add(r.metric_name);
    }
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
      <td><div class="mpfm-origin-cell">${mpfmSourceBadge(r.source_kind, r.is_adjusted)}<div class="mpfm-origin-meta" title="${escapeHtml(r.source_file||'')}">${escapeHtml(r.adjustment_source || r.source_file || 'sem arquivo')}</div></div></td>
      ${sel.map(m => {
        const id = r[`__id_${m}`];
        const v  = r[m];
        const adjusted = r.__adjusted_metrics?.has?.(m);
        const source = adjusted ? (r[`__adjustment_source_${m}`] || r[`__source_${m}`] || 'Registro de ajustes') : '';
        return `<td class="num" id="mc_${id||'_'+ri+'_'+escapeHtml(m)}" style="cursor:${id?'pointer':'default'}"
          ${adjusted ? `data-adjusted="1"` : ''}
          ${id ? `onclick="editMeasurement(${id}, this, '${jsStr(m)}', '${jsStr(r.day_ref)}', ${r.hour_ref??'null'}, '${jsStr(r.bank)}', 'mpfm')" title="${adjusted ? `Corrigido por registro de ajustes: ${escapeHtml(source)}. ` : ''}Clique para editar"` : ''}>${adjusted ? '<span class="mpfm-adjusted-dot" title="Valor corrigido por registro de ajustes">●</span>' : ''}${fmt(v)}</td>`;
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

function mpfmAdjustmentQs() {
  return new URLSearchParams({
    date_from: document.getElementById('mDateFrom').value,
    date_to:   document.getElementById('mDateTo').value,
    bank:      document.getElementById('mBank').value,
    tag:       document.getElementById('mTag').value || '',
  });
}

function setMpfmAdjustmentStatus(message, kind = '') {
  const host = document.getElementById('mpfmAdjustmentStatus');
  if (!host) return;
  host.textContent = message;
  host.style.color = kind === 'error' ? '#ff8a8a' : kind === 'success' ? '#7bd88f' : '';
}

function getMpfmAdjustmentFile() {
  const input = document.getElementById('mpfmAdjustmentFile');
  return input?.files?.[0] || null;
}

async function sendMpfmAdjustmentFile(endpoint, extra = {}) {
  const file = getMpfmAdjustmentFile();
  if (!file) throw new Error('Selecione um arquivo .xlsx de ajustes MPFM antes de continuar.');
  const form = new FormData();
  form.append('file', file);
  Object.entries(extra).forEach(([key, value]) => form.append(key, value ?? ''));
  const res = await fetch(`${API}${endpoint}`, {method: 'POST', body: form});
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(payload.detail || payload.message || 'Falha ao processar o arquivo de ajustes.');
  return payload;
}

document.getElementById('btnExportMpfmAdjustments').onclick = () => {
  window.open(`${API}/mpfm-adjustments/export?${mpfmAdjustmentQs()}`, '_blank');
};
document.getElementById('btnPickMpfmAdjustment').onclick = () => document.getElementById('mpfmAdjustmentFile')?.click();
document.getElementById('mpfmAdjustmentFile').onchange = () => {
  const file = getMpfmAdjustmentFile();
  setMpfmAdjustmentStatus(file ? `Registro de ajustes selecionado: ${file.name}` : 'Registro de ajustes: nenhum arquivo selecionado.');
};
document.getElementById('btnPreviewMpfmAdjustment').onclick = async () => {
  try {
    setMpfmAdjustmentStatus('Validando arquivo de ajustes…');
    const payload = await sendMpfmAdjustmentFile('/mpfm-adjustments/import/preview');
    setMpfmAdjustmentStatus(`Prévia: ${payload.rows_marked || 0} linha(s) marcadas; ${payload.metrics_changed || 0} métrica(s) seriam alteradas; ${(payload.skipped || []).length} item(ns) ignorado(s).`, 'success');
  } catch (error) {
    console.error('Falha na prévia do registro de ajustes MPFM', error);
    setMpfmAdjustmentStatus(error?.message || 'Falha na prévia do registro de ajustes.', 'error');
  }
};
document.getElementById('btnApplyMpfmAdjustment').onclick = async () => {
  try {
    const file = getMpfmAdjustmentFile();
    if (!file) throw new Error('Selecione um arquivo .xlsx de ajustes MPFM antes de continuar.');
    const author = prompt('Responsável pelo ajuste:', '') || '';
    const ok = confirm(`Aplicar correções do arquivo ${file.name}?\n\nEsta ação atualiza as métricas marcadas com ajustar=Sim e registra auditoria dos valores antigos e novos.`);
    if (!ok) return;
    setMpfmAdjustmentStatus('Aplicando ajustes MPFM…');
    const payload = await sendMpfmAdjustmentFile('/mpfm-adjustments/import/apply', {author});
    setMpfmAdjustmentStatus(`Ajustes aplicados: ${payload.metrics_changed || 0} métrica(s), ${payload.rows_marked || 0} linha(s) marcadas. Import ID ${payload.import_id || '—'}.`, 'success');
    await loadMPFM(true);
    await notifyDataChanged(['mpfm','resumo','cards','monitoramento','xml042','exportar','recon']);
  } catch (error) {
    console.error('Falha ao aplicar registro de ajustes MPFM', error);
    setMpfmAdjustmentStatus(error?.message || 'Falha ao aplicar o registro de ajustes.', 'error');
  }
};

